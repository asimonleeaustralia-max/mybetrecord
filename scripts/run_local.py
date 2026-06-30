#!/usr/bin/env python3
"""
Run the whole app locally without Docker.

Launches the four FastAPI services on 8001-8004 and a tiny static-file +
reverse-proxy server on 8080 that stands in for nginx, backed by a single
SQLite file so there's no database to install. Intended for quick local
development; production still uses docker-compose / Azure + PostgreSQL.

    pip install ./shared
    pip install -r services/auth/requirements.txt \
                -r services/bets/requirements.txt \
                -r services/reports/requirements.txt \
                -r services/payments/requirements.txt
    python scripts/run_local.py

Then open http://localhost:8080
"""

from __future__ import annotations

import http.server
import os
import signal
import socketserver
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"
DB_PATH = ROOT / "betrecord.local.db"

FRONTEND_PORT = 8080
SERVICES = {  # name -> port
    "auth": 8001,
    "bets": 8002,
    "reports": 8003,
    "payments": 8004,
}
PROXY_PREFIXES = {
    "/auth": 8001,
    "/bets": 8002,
    "/reports": 8003,
    "/payments": 8004,
}

ENV = {
    **os.environ,
    "DATABASE_URL": f"sqlite+pysqlite:///{DB_PATH}",
    "ENVIRONMENT": "development",
    "JWT_SECRET": os.environ.get("JWT_SECRET", "local-dev-secret-please-change-0123456789"),
    "CORS_ORIGINS": "*",
}


def prepare_db() -> None:
    """Create the SQLite schema once, up front, so the four service processes
    don't race each other to create tables on first boot."""
    os.environ["DATABASE_URL"] = ENV["DATABASE_URL"]  # must be set before import
    try:
        from betrecord_shared.database import init_db
        init_db()
        print("  · database schema ready")
    except Exception as e:  # shared not importable yet — services will handle it
        print(f"  · pre-init skipped ({e}); services will create the schema")


def start_services() -> list[subprocess.Popen]:
    procs = []
    for name, port in SERVICES.items():
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--app-dir", str(ROOT / "services" / name),
             "--host", "127.0.0.1", "--port", str(port)],
            env=ENV,
        )
        procs.append(proc)
        print(f"  · {name} starting on :{port}")
    return procs


def wait_for_services(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    pending = dict(SERVICES)
    while pending and time.time() < deadline:
        for name, port in list(pending.items()):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                print(f"  · {name} ready")
                del pending[name]
            except Exception:
                pass
        if pending:
            time.sleep(0.5)
    if pending:
        print(f"  ! still waiting on: {', '.join(pending)} (continuing anyway)")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    # ---- proxying ----
    def _proxy_target(self):
        for prefix, port in PROXY_PREFIXES.items():
            if self.path == prefix or self.path.startswith(prefix + "/") or \
               (prefix == "/bets" and self.path.startswith("/bets")):
                return port
        return None

    def _do_proxy(self, port: int):
        body = None
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            body = self.rfile.read(length)
        url = f"http://127.0.0.1:{port}{self.path}"
        req = urllib.request.Request(url, data=body, method=self.command)
        for h in ("Authorization", "Content-Type", "X-API-Key", "Accept", "User-Agent"):
            if h in self.headers:
                req.add_header(h, self.headers[h])
        client_ip = self.client_address[0]
        if client_ip:
            req.add_header("X-Forwarded-For", client_ip)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() in ("transfer-encoding", "connection"):
                        continue
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            payload = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:  # service down
            msg = f'{{"detail":"proxy error: {e}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(msg)

    def _share_token(self, path: str) -> str | None:
        if path.startswith("/share/"):
            token = path[len("/share/"):].split("/")[0].split("?")[0]
            return token or None
        return None

    def _rewrite_path(self, path: str) -> str:
        """Map public URLs to static files or SPA fallbacks."""
        if path in ("/privacy", "/terms", "/support", "/login"):
            return f"{path}.html"
        if path.startswith("/app/"):
            rel = path.lstrip("/")
            target = PUBLIC / rel
            if path != "/app/" and not target.is_file():
                return "/app/index.html"
            return path
        if path.startswith("/blog/"):
            if path.endswith("/"):
                return "/blog/index.html"
            rel = path.lstrip("/")
            target = PUBLIC / rel
            if target.is_file():
                return path
            html_target = PUBLIC / f"{rel}.html"
            if html_target.is_file():
                return f"/{rel}.html"
            return "/blog/index.html"
        if path.startswith("/pricing/"):
            if path.endswith("/"):
                return "/pricing/index.html"
            rel = path.lstrip("/")
            target = PUBLIC / rel
            if target.is_file():
                return path
            html_target = PUBLIC / f"{rel}.html"
            if html_target.is_file():
                return f"/{rel}.html"
            return "/pricing/index.html"
        if path != "/" and not (PUBLIC / path.lstrip("/")).is_file():
            # Marketing root only — do not SPA-fallback unknown paths to ledger.
            if path.endswith((".css", ".js", ".svg", ".txt", ".xml", ".json", ".html")):
                return path
        return path

    def _dispatch(self):
        path = self.path.split("?")[0]
        share = self._share_token(path)
        if share:
            saved = self.path
            self.path = f"/bets/share-page/{share}"
            self._do_proxy(8002)
            self.path = saved
            return True
        port = self._proxy_target()
        if port:
            self._do_proxy(port)
            return True
        return False

    def do_GET(self):
        if self._dispatch():
            return
        path = self.path.split("?")[0]
        self.path = self._rewrite_path(path)
        super().do_GET()

    def do_POST(self):
        if not self._dispatch():
            self.send_error(404)

    def do_PATCH(self):
        if not self._dispatch():
            self.send_error(404)

    def do_DELETE(self):
        if not self._dispatch():
            self.send_error(404)

    def end_headers(self):
        path = self.path.split("?")[0]
        if path.startswith("/app/") or path in ("/app/index.html",):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        elif path.endswith((".html", ".js", ".css")):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter logs
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    print("Starting mybetrecord locally (SQLite, no Docker)…")
    prepare_db()
    procs = start_services()
    wait_for_services(timeout=15.0)

    httpd = Server(("127.0.0.1", FRONTEND_PORT), Handler)
    print(f"\n  ➜  http://localhost:{FRONTEND_PORT}\n  (Ctrl-C to stop)\n")

    def shutdown(*_):
        print("\nStopping…")
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()
        os._exit(0)  # avoid httpd.shutdown() deadlock from within the handler

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        httpd.serve_forever()
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()

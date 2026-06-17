"""Shared fixtures for the integration tests.

Each service is its own FastAPI app in a package named `app`, so loading more
than one in the same interpreter needs the `app*` modules evicted from
sys.modules between imports. All four apps are pointed at a single in-memory
SQLite database (StaticPool keeps it alive across connections) so a token or
API key minted by `auth` is visible to `bets` and `reports`, exactly as it is
in production where they share PostgreSQL.
"""

from __future__ import annotations

import importlib
import os
import sys
import uuid

import pytest

# Must be set before betrecord_shared.config is imported (it reads env at import).
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("JWT_SECRET", "integration-test-secret-key-0123456789abcd")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from betrecord_shared import database

# One in-memory DB shared by every service app.
_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
database.engine = _engine
database.SessionLocal = sessionmaker(
    bind=_engine, autoflush=False, expire_on_commit=False, future=True
)
database.init_db()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_app(service: str):
    for mod in [k for k in list(sys.modules) if k == "app" or k.startswith("app.")]:
        del sys.modules[mod]
    sys.path.insert(0, os.path.join(ROOT, "services", service))
    try:
        module = importlib.import_module("app.main")
    finally:
        sys.path.pop(0)
    return module.app


@pytest.fixture(scope="session")
def clients() -> dict[str, TestClient]:
    return {
        "auth": TestClient(_load_app("auth")),
        "bets": TestClient(_load_app("bets")),
        "reports": TestClient(_load_app("reports")),
        "payments": TestClient(_load_app("payments")),
    }


@pytest.fixture
def auth_headers(clients):
    """Register a fresh user and return (headers, email)."""
    email = f"user-{uuid.uuid4().hex[:10]}@example.com"
    r = clients["auth"].post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email

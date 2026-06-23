#!/usr/bin/env python3
"""Build static blog HTML and sitemap from content/blog/*.md."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "blog"
TEMPLATE_DIR = ROOT / "scripts" / "blog_templates"
OUT_DIR = ROOT / "frontend" / "public" / "blog"
PUBLIC_DIR = ROOT / "frontend" / "public"
SITE_URL = "https://mybetrecord.com"

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip('"').strip("'")
    body = text[m.end() :]
    return meta, body


def load_posts() -> list[dict]:
    posts = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        slug = meta.get("slug") or path.stem
        posts.append(
            {
                "slug": slug,
                "title": meta.get("title", slug.replace("-", " ").title()),
                "description": meta.get("description", ""),
                "date": meta.get("date", "2026-01-01"),
                "keywords": meta.get("keywords", ""),
                "body_html": markdown.markdown(
                    body,
                    extensions=["extra", "smarty", "sane_lists"],
                ),
            }
        )
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build() -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    post_tpl = env.get_template("post.html")
    index_tpl = env.get_template("index.html")
    sitemap_tpl = env.get_template("sitemap.xml")

    posts = load_posts()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, post in enumerate(posts):
        related = [p for j, p in enumerate(posts) if j != i][:2]
        html = post_tpl.render(
            site_url=SITE_URL,
            post=post,
            related=related,
            build_date=date.today().isoformat(),
        )
        (OUT_DIR / f"{post['slug']}.html").write_text(html, encoding="utf-8")

    index_html = index_tpl.render(site_url=SITE_URL, posts=posts)
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    static_urls = [
        {"loc": f"{SITE_URL}/", "changefreq": "weekly", "priority": "1.0"},
        {"loc": f"{SITE_URL}/login", "changefreq": "monthly", "priority": "0.5"},
        {"loc": f"{SITE_URL}/privacy", "changefreq": "yearly", "priority": "0.3"},
        {"loc": f"{SITE_URL}/terms", "changefreq": "yearly", "priority": "0.3"},
        {"loc": f"{SITE_URL}/blog/", "changefreq": "weekly", "priority": "0.8"},
        {"loc": f"{SITE_URL}/pricing/", "changefreq": "monthly", "priority": "0.8"},
    ]
    for post in posts:
        static_urls.append(
            {
                "loc": f"{SITE_URL}/blog/{post['slug']}.html",
                "changefreq": "monthly",
                "priority": "0.7",
                "lastmod": post["date"],
            }
        )

    sitemap = sitemap_tpl.render(urls=static_urls)
    (PUBLIC_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print(f"Built {len(posts)} blog posts + sitemap.xml")


if __name__ == "__main__":
    build()

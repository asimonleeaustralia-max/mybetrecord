"""Configuration shared by every service, sourced from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://betrecord:betrecord@localhost:5432/betrecord",
    )

    # Auth
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
    password_reset_minutes: int = int(os.getenv("PASSWORD_RESET_MINUTES", "60"))
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:8080")

    # Email (optional — password reset falls back to logging in development)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@mybetrecord.com")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    # CORS
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]

    # Service discovery (set per environment; localhost for docker-compose)
    auth_url: str = os.getenv("AUTH_URL", "http://localhost:8001")
    bets_url: str = os.getenv("BETS_URL", "http://localhost:8002")
    reports_url: str = os.getenv("REPORTS_URL", "http://localhost:8003")
    payments_url: str = os.getenv("PAYMENTS_URL", "http://localhost:8004")

    # Stripe (payments service)
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_id: str = os.getenv("STRIPE_PRICE_ID", "")
    # Existing Stripe Product to attach Pro prices to. Optional — when unset the
    # payments service creates the line item with inline product data instead.
    stripe_product_id: str = os.getenv("STRIPE_PRODUCT_ID", "")

    # Free plan limits. Free users may enter at most this many single bets per
    # day, plus a separate daily allowance of multiple/parlay bets; Pro users
    # are unlimited. The main functional difference between the plans.
    free_daily_bet_limit: int = int(os.getenv("FREE_DAILY_BET_LIMIT", "5"))
    free_daily_multiple_limit: int = int(os.getenv("FREE_DAILY_MULTIPLE_LIMIT", "5"))

    # Multiple / parlay leg bounds. A multiple is at least a double (2 legs) and
    # at most this many legs.
    min_parlay_legs: int = 2
    max_parlay_legs: int = int(os.getenv("MAX_PARLAY_LEGS", "10"))

    environment: str = os.getenv("ENVIRONMENT", "development")

    # Comma-separated emails that are always granted admin on login/startup.
    bootstrap_admin_emails: list[str] = [
        e.strip().lower()
        for e in os.getenv("BOOTSTRAP_ADMIN_EMAILS", "asimonlee@gmail.com").split(",")
        if e.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()

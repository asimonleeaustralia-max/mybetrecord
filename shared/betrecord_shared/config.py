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

    environment: str = os.getenv("ENVIRONMENT", "development")


@lru_cache
def get_settings() -> Settings:
    return Settings()

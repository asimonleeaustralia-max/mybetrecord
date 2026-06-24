"""Configuration shared by every service, sourced from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        # Database
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://betrecord:betrecord@localhost:5432/betrecord",
        )

        # Auth
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
        self.password_reset_minutes = int(os.getenv("PASSWORD_RESET_MINUTES", "60"))
        self.email_verification_minutes = int(os.getenv("EMAIL_VERIFICATION_MINUTES", "1440"))
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8080")

        # Email (optional — password reset falls back to logging in development)
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_from = os.getenv("SMTP_FROM", "noreply@mybetrecord.com")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

        # CORS
        self.cors_origins = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "*").split(",")
            if o.strip()
        ]

        # Service discovery (set per environment; localhost for docker-compose)
        self.auth_url = os.getenv("AUTH_URL", "http://localhost:8001")
        self.bets_url = os.getenv("BETS_URL", "http://localhost:8002")
        self.reports_url = os.getenv("REPORTS_URL", "http://localhost:8003")
        self.payments_url = os.getenv("PAYMENTS_URL", "http://localhost:8004")

        # Stripe (payments service)
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.stripe_price_id = os.getenv("STRIPE_PRICE_ID", "")
        # Existing Stripe Product to attach Pro prices to. Optional — when unset the
        # payments service creates the line item with inline product data instead.
        self.stripe_product_id = os.getenv("STRIPE_PRODUCT_ID", "")

        # Free plan limits. Free users may enter at most this many single bets per
        # day, plus a separate daily allowance of multiple/parlay bets; Pro users
        # are unlimited. The main functional difference between the plans.
        self.free_daily_bet_limit = int(os.getenv("FREE_DAILY_BET_LIMIT", "5"))
        self.free_daily_multiple_limit = int(os.getenv("FREE_DAILY_MULTIPLE_LIMIT", "5"))

        # Multiple / parlay leg bounds. A multiple is at least a double (2 legs) and
        # at most this many legs.
        self.min_parlay_legs = 2
        self.max_parlay_legs = int(os.getenv("MAX_PARLAY_LEGS", "10"))

        self.environment = os.getenv("ENVIRONMENT", "development")

    # Comma-separated emails that are always granted admin on login/startup.
    @property
    def bootstrap_admin_emails(self) -> list[str]:
        return [
            e.strip().lower()
            for e in os.getenv("BOOTSTRAP_ADMIN_EMAILS", "asimonlee@gmail.com").split(",")
            if e.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()

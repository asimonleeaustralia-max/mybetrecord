"""Development-only data seeding."""

from __future__ import annotations

from sqlalchemy import inspect, select, text

from .config import get_settings
from .database import SessionLocal, engine
from .models import User

DEV_ADMIN_EMAIL = "admin@admin.com"
DEV_ADMIN_PASSWORD = "password"


def _ensure_is_admin_column() -> None:
    """Add is_admin to existing databases created before the column existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    if "is_admin" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin "
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
            )


def _ensure_bookmaker_column() -> None:
    """Add bookmaker to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "bookmaker" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS bookmaker VARCHAR(80)"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN bookmaker VARCHAR(80)"))


def _ensure_settled_at_column() -> None:
    """Add settled_at to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "settled_at" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN settled_at TIMESTAMP WITH TIME ZONE"))
            conn.execute(text("UPDATE bets SET settled_at = placed_at"))
            conn.execute(text("ALTER TABLE bets ALTER COLUMN settled_at SET NOT NULL"))
            conn.execute(text("ALTER TABLE bets ALTER COLUMN settled_at SET DEFAULT NOW()"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN settled_at DATETIME"))
            conn.execute(text("UPDATE bets SET settled_at = placed_at"))


def _migrate_exchange_to_bookmaker() -> None:
    """Copy legacy exchange names into bookmaker for existing databases."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "exchange" not in columns:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE bets SET bookmaker = exchange "
                "WHERE exchange IS NOT NULL AND exchange != '' "
                "AND (bookmaker IS NULL OR bookmaker = '')"
            )
        )


def _ensure_last_login_at_column() -> None:
    """Add last_login_at to existing databases created before the column existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    if "last_login_at" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE")
            )
        else:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))


def seed_dev_admin() -> None:
    """Create a default admin account for local development."""
    if get_settings().environment == "production":
        return

    from .security import hash_password

    _ensure_is_admin_column()
    _ensure_bookmaker_column()
    _ensure_settled_at_column()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == DEV_ADMIN_EMAIL))
        if user:
            if not user.is_admin:
                user.is_admin = True
                db.commit()
            return

        db.add(
            User(
                email=DEV_ADMIN_EMAIL,
                password_hash=hash_password(DEV_ADMIN_PASSWORD),
                display_name="Admin",
                is_admin=True,
            )
        )
        db.commit()

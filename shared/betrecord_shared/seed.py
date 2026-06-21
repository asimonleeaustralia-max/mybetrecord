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


def _ensure_event_at_column() -> None:
    """Add event_at to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "event_at" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS event_at TIMESTAMP WITH TIME ZONE"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN event_at DATETIME"))


def _ensure_tournament_column() -> None:
    """Add tournament to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "tournament" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS tournament VARCHAR(255)"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN tournament VARCHAR(255)"))


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


def _ensure_closing_odds_exchange_column() -> None:
    """Add closing_odds_exchange to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "closing_odds_exchange" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS closing_odds_exchange FLOAT"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN closing_odds_exchange FLOAT"))


def _ensure_timezone_column() -> None:
    """Add timezone to existing databases created before the column existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    if "timezone" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone "
                    "VARCHAR(64) NOT NULL DEFAULT 'UTC'"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'UTC'")
            )


def _ensure_preferred_locale_column() -> None:
    """Add preferred_locale to existing databases created before the column existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    if "preferred_locale" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_locale "
                    "VARCHAR(16) NOT NULL DEFAULT 'en'"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN preferred_locale VARCHAR(16) NOT NULL DEFAULT 'en'")
            )


def _ensure_share_token_column() -> None:
    """Add share_token to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "share_token" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS share_token VARCHAR(32)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_bets_share_token ON bets (share_token)"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN share_token VARCHAR(32)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_bets_share_token ON bets (share_token)"))


def _ensure_modelling_edge_columns() -> None:
    """Add edge and model Kelly columns to existing databases."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    dialect = engine.dialect.name
    additions = [
        ("personal_edge_pct", "FLOAT"),
        ("model_edge_pct", "FLOAT"),
        ("model_kelly_stake", "FLOAT"),
    ]
    pending = [(name, sql_type) for name, sql_type in additions if name not in columns]
    if not pending:
        return
    with engine.begin() as conn:
        for name, sql_type in pending:
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE bets ADD COLUMN IF NOT EXISTS {name} {sql_type}"))
            else:
                conn.execute(text(f"ALTER TABLE bets ADD COLUMN {name} {sql_type}"))


def _ensure_bet_broker_column() -> None:
    """Add bet_broker to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "bet_broker" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS bet_broker VARCHAR(120)"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN bet_broker VARCHAR(120)"))


def _ensure_side_column() -> None:
    """Add side (back|lay) to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "side" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE bets ADD COLUMN IF NOT EXISTS side VARCHAR(8) "
                    "NOT NULL DEFAULT 'back'"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE bets ADD COLUMN side VARCHAR(8) NOT NULL DEFAULT 'back'")
            )
        conn.execute(text("UPDATE bets SET side = 'lay' WHERE LOWER(bet_type) = 'lay'"))


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

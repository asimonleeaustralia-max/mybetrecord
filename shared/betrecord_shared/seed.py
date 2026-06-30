"""Development-only data seeding."""

from __future__ import annotations

from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from .config import get_settings
from .database import SessionLocal, engine
from .models import User

DEV_ADMIN_EMAIL = "admin@admin.com"
DEV_ADMIN_PASSWORD = "password"


def is_bootstrap_admin_email(email: str) -> bool:
    return email.lower() in get_settings().bootstrap_admin_emails


def promote_bootstrap_admin(user: User, db) -> bool:
    """Grant admin to bootstrap emails. Returns True if the user was promoted."""
    if user.is_admin or not is_bootstrap_admin_email(user.email):
        return False
    user.is_admin = True
    db.flush()
    return True


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


def _ensure_portal_column() -> None:
    """Add portal to existing databases created before the column existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "portal" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(text("ALTER TABLE bets ADD COLUMN IF NOT EXISTS portal VARCHAR(16)"))
        else:
            conn.execute(text("ALTER TABLE bets ADD COLUMN portal VARCHAR(16)"))


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


def _ensure_is_multiple_column() -> None:
    """Add is_multiple to existing databases created before parlays existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "is_multiple" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE bets ADD COLUMN IF NOT EXISTS is_multiple "
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE bets ADD COLUMN is_multiple BOOLEAN NOT NULL DEFAULT 0")
            )


def _ensure_free_bet_column() -> None:
    """Add free_bet to existing databases created before promotions existed."""
    if "bets" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("bets")}
    if "free_bet" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE bets ADD COLUMN IF NOT EXISTS free_bet "
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
        else:
            conn.execute(
                text("ALTER TABLE bets ADD COLUMN free_bet BOOLEAN NOT NULL DEFAULT 0")
            )


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


def _ensure_billing_columns() -> None:
    """Add subscription/billing columns to databases created before they existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    dialect = engine.dialect.name
    # (name, postgres type, sqlite type)
    additions = [
        ("plan", "VARCHAR(16) NOT NULL DEFAULT 'free'", "VARCHAR(16) NOT NULL DEFAULT 'free'"),
        ("plan_currency", "VARCHAR(3)", "VARCHAR(3)"),
        ("stripe_customer_id", "VARCHAR(64)", "VARCHAR(64)"),
        ("stripe_subscription_id", "VARCHAR(64)", "VARCHAR(64)"),
        ("subscription_status", "VARCHAR(32)", "VARCHAR(32)"),
        (
            "subscription_cancel_at_period_end",
            "BOOLEAN NOT NULL DEFAULT FALSE",
            "BOOLEAN NOT NULL DEFAULT 0",
        ),
        (
            "subscription_current_period_end",
            "TIMESTAMP WITH TIME ZONE",
            "DATETIME",
        ),
    ]
    pending = [a for a in additions if a[0] not in columns]
    if not pending:
        return
    with engine.begin() as conn:
        for name, pg_type, sqlite_type in pending:
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {pg_type}"))
            else:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {sqlite_type}"))
        if dialect == "postgresql":
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users (stripe_customer_id)")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_users_stripe_subscription_id "
                    "ON users (stripe_subscription_id)"
                )
            )


def _ensure_comp_pro_until_column() -> None:
    """Add comp_pro_until to existing databases created before the column existed."""
    if "users" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    if "comp_pro_until" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS comp_pro_until "
                    "TIMESTAMP WITH TIME ZONE"
                )
            )
        else:
            conn.execute(text("ALTER TABLE users ADD COLUMN comp_pro_until DATETIME"))


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


def _ensure_landing_promo_column() -> None:
    """Add promo_code to landing_hits for promo referral tracking."""
    if "landing_hits" not in inspect(engine).get_table_names():
        return
    columns = {c["name"] for c in inspect(engine).get_columns("landing_hits")}
    if "promo_code" in columns:
        return
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text("ALTER TABLE landing_hits ADD COLUMN IF NOT EXISTS promo_code VARCHAR(64)")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_landing_hits_promo_code "
                    "ON landing_hits (promo_code)"
                )
            )
        else:
            conn.execute(text("ALTER TABLE landing_hits ADD COLUMN promo_code VARCHAR(64)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_landing_hits_promo_code ON landing_hits (promo_code)"))


def seed_bootstrap_admins() -> None:
    """Promote configured bootstrap emails to admin if the account exists."""
    emails = get_settings().bootstrap_admin_emails
    if not emails:
        return

    _ensure_is_admin_column()

    with SessionLocal() as db:
        changed = False
        for email in emails:
            user = db.scalar(select(User).where(User.email == email))
            if user and promote_bootstrap_admin(user, db):
                changed = True
        if changed:
            db.commit()


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

        try:
            db.add(
                User(
                    email=DEV_ADMIN_EMAIL,
                    password_hash=hash_password(DEV_ADMIN_PASSWORD),
                    is_admin=True,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()

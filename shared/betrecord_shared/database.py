"""SQLAlchemy engine + session factory shared across services."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from .config import get_settings

settings = get_settings()

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    # run_local.py shares one SQLite file across four processes
    _connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. Production uses Alembic instead."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    from . import models  # noqa: F401  (ensure models are registered)
    from .seed import (
        seed_dev_admin,
        _migrate_exchange_to_bookmaker,
        _ensure_closing_odds_exchange_column,
        _ensure_last_login_at_column,
        _ensure_preferred_locale_column,
        _ensure_settled_at_column,
    )

    if settings.database_url.startswith("postgresql"):
        # Four services can start together on docker-compose; without a lock,
        # concurrent create_all() calls race and Postgres raises UniqueViolation.
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(78901234)"))
            try:
                Base.metadata.create_all(bind=conn)
            except IntegrityError:
                pass
    else:
        try:
            Base.metadata.create_all(bind=engine)
        except IntegrityError:
            pass

    _migrate_exchange_to_bookmaker()
    _ensure_settled_at_column()
    _ensure_closing_odds_exchange_column()
    _ensure_last_login_at_column()
    _ensure_preferred_locale_column()
    seed_dev_admin()

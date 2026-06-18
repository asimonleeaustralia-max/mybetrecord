"""Database models. Two services own writes here: auth (users/api keys) and
bets (bets). Reports reads only. Keeping one model module keeps the betting
schema authoritative in a single place; each service imports what it needs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Settings
    default_odds_format: Mapped[str] = mapped_column(String(16), default="decimal")  # decimal|american|fractional
    base_currency: Mapped[str] = mapped_column(String(3), default="GBP")
    bankroll: Mapped[float] = mapped_column(Float, default=0.0)
    kelly_multiplier: Mapped[float] = mapped_column(Float, default=1.0)  # 1=full, .5=half

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bets: Mapped[list["Bet"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="default")
    prefix: Mapped[str] = mapped_column(String(12), index=True)   # shown to user, e.g. mbr_ab12cd
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # only the hash is stored
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="api_keys")


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # What was bet
    event: Mapped[str] = mapped_column(String(255), nullable=False)
    selection: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    bet_type: Mapped[str] = mapped_column(String(80), default="Win")
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    # Odds — stored canonically as decimal; the entry format is remembered for display.
    odds_decimal: Mapped[float] = mapped_column(Float, nullable=False)
    odds_format: Mapped[str] = mapped_column(String(16), default="decimal")

    # Stake & money
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")

    # Each-way support
    each_way: Mapped[bool] = mapped_column(Boolean, default=False)
    place_fraction: Mapped[float] = mapped_column(Float, default=0.25)
    placed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Settlement
    outcome: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # win|loss|void|...
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    profit: Mapped[float] = mapped_column(Float, default=0.0)   # computed, net of commission
    cash_out_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Modelling / analytics
    bet_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_implied_odds: Mapped[float | None] = mapped_column(Float, nullable=True)     # decimal
    personal_implied_odds: Mapped[float | None] = mapped_column(Float, nullable=True)  # decimal
    kelly_stake: Mapped[float | None] = mapped_column(Float, nullable=True)            # computed
    closing_odds: Mapped[float | None] = mapped_column(Float, nullable=True)           # decimal

    # Where the bet was placed
    bookmaker: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    exchange_commission_pct: Mapped[float] = mapped_column(Float, default=0.0)  # % deducted from winnings

    # Meta
    tipster: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="bets")

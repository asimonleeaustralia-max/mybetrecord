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
    account_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settings
    default_odds_format: Mapped[str] = mapped_column(String(16), default="decimal")  # decimal|american|fractional|hong_kong|malaysian|indonesian
    base_currency: Mapped[str] = mapped_column(String(3), default="GBP")
    bankroll: Mapped[float] = mapped_column(Float, default=0.0)
    kelly_multiplier: Mapped[float] = mapped_column(Float, default=1.0)  # 1=full, .5=half
    preferred_locale: Mapped[str] = mapped_column(String(16), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")  # IANA, e.g. Europe/London

    # Public read-only bet record (unguessable token; null when disabled)
    public_bets_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    public_bets_token: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Billing / subscription. Free is the default; Pro lifts the weekly bet cap.
    # Stripe is the source of truth — these fields cache its state so the rest
    # of the app can gate features without calling Stripe on every request.
    plan: Mapped[str] = mapped_column(String(16), default="free")  # free | pro
    plan_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subscription_cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Admin-granted complimentary Pro access (independent of Stripe subscription).
    comp_pro_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_pro(self) -> bool:
        if (self.plan or "free").lower() == "pro":
            return True
        until = self.comp_pro_until
        if until is None:
            return False
        now = datetime.now(timezone.utc)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > now

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bets: Mapped[list["Bet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PendingRegistration(Base):
    """Signup held until the user verifies their email address."""

    __tablename__ = "pending_registrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")


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


class LandingHit(Base):
    """Anonymous visit to the marketing home page (no account required)."""

    __tablename__ = "landing_hits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    path: Mapped[str] = mapped_column(String(255), default="/", index=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    promo_code: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class PromoCode(Base):
    """Admin-managed promotion code for Pro subscriptions."""

    __tablename__ = "promo_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    promo_type: Mapped[str] = mapped_column(String(32), nullable=False)  # free_months | percent_discount
    free_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percent_off: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    stripe_coupon_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stripe_promotion_code_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stats_token: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    redemptions: Mapped[list["PromoRedemption"]] = relationship(
        back_populates="promo_code", cascade="all, delete-orphan"
    )


class PromoRedemption(Base):
    """Record of a promo code applied at checkout — one row per user per code."""

    __tablename__ = "promo_redemptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    promo_code_id: Mapped[str] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    promo_code: Mapped["PromoCode"] = relationship(back_populates="redemptions")
    user: Mapped["User"] = relationship()


class AppEvent(Base):
    __tablename__ = "app_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    user: Mapped["User | None"] = relationship()


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # What was bet
    tournament: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event: Mapped[str] = mapped_column(String(255), nullable=False)
    selection: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    bet_type: Mapped[str] = mapped_column(String(80), default="Win")
    side: Mapped[str] = mapped_column(String(8), default="back", index=True)  # back | lay
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Multiple / parlay: when true, the bet combines 2+ selections (see BetLeg).
    # The single event/selection/odds fields below carry a summary and the
    # combined decimal odds (the product of every leg's price) for back-compat
    # with the ledger, reports, exports, and share links.
    is_multiple: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

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

    # Promotion: stake is not returned; losses record zero P/L.
    free_bet: Mapped[bool] = mapped_column(Boolean, default=False)

    # Settlement
    outcome: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # win|loss|void|...
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    profit: Mapped[float] = mapped_column(Float, default=0.0)   # computed, net of commission
    cash_out_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Modelling / analytics
    bet_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_implied_odds: Mapped[float | None] = mapped_column(Float, nullable=True)     # decimal
    personal_implied_odds: Mapped[float | None] = mapped_column(Float, nullable=True)  # decimal
    personal_edge_pct: Mapped[float | None] = mapped_column(Float, nullable=True)        # computed
    model_edge_pct: Mapped[float | None] = mapped_column(Float, nullable=True)           # computed
    kelly_stake: Mapped[float | None] = mapped_column(Float, nullable=True)            # personal Kelly stake
    model_kelly_stake: Mapped[float | None] = mapped_column(Float, nullable=True)      # model Kelly stake
    closing_odds: Mapped[float | None] = mapped_column(Float, nullable=True)           # decimal, bookmaker
    closing_odds_exchange: Mapped[float | None] = mapped_column(Float, nullable=True)  # decimal, exchange

    # Where the bet was placed
    bookmaker: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    portal: Mapped[str | None] = mapped_column(String(16), nullable=True)  # phone | online | in_shop
    exchange_commission_pct: Mapped[float] = mapped_column(Float, default=0.0)  # % deducted from winnings

    # Meta
    tipster: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bet_broker: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Public share link (unguessable token; null when sharing is disabled)
    share_token: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="bets")
    legs: Mapped[list["BetLeg"]] = relationship(
        back_populates="bet",
        cascade="all, delete-orphan",
        order_by="BetLeg.leg_index",
        lazy="selectin",
    )


class BetLeg(Base):
    """One selection (leg) of a multiple / parlay bet.

    Singles have no legs. A multiple stores one row per selection here; the
    parent Bet keeps the combined decimal odds (product of all leg prices) so
    settlement, reporting, and sharing stay unchanged.
    """

    __tablename__ = "bet_legs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    bet_id: Mapped[str] = mapped_column(ForeignKey("bets.id", ondelete="CASCADE"), index=True)
    leg_index: Mapped[int] = mapped_column(Integer, default=0)  # 0-based order within the bet

    event: Mapped[str] = mapped_column(String(255), nullable=False)
    selection: Mapped[str] = mapped_column(String(255), nullable=False)

    # Odds — stored canonically as decimal; the entry format is remembered for display.
    odds_decimal: Mapped[float] = mapped_column(Float, nullable=False)
    odds_format: Mapped[str] = mapped_column(String(16), default="decimal")

    bet: Mapped["Bet"] = relationship(back_populates="legs")

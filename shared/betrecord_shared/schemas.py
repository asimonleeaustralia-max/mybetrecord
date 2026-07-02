"""Pydantic v2 schemas shared by the services."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator

ODDS_FORMAT_PATTERN = (
    "^(decimal|american|fractional|hong_kong|malaysian|indonesian)$"
)
PORTAL_PATTERN = "^(phone|online|in_shop)$"


# ----------------------------- Auth / users ------------------------------- #

_HAS_DIGIT = re.compile(r"\d")
_HAS_SPECIAL = re.compile(r"[^a-zA-Z0-9]")


def _validate_password(value: str) -> str:
    if not (_HAS_DIGIT.search(value) or _HAS_SPECIAL.search(value)):
        raise ValueError("Password must include at least one number or special character")
    return value


def _validate_iana_timezone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Invalid timezone") from exc
    return value


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: Optional[str] = Field(default=None, max_length=64)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str | None) -> str | None:
        return _validate_iana_timezone(v)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterResponse(BaseModel):
    message: str
    verification_token: Optional[str] = None  # populated in non-production for local testing


class VerifyEmailConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _validate_password(v)


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None  # populated in non-production for local testing


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return _validate_password(v)


LOCALE_PATTERN = r"^[a-z]{2,3}(-[A-Z]{2})?$"


class SettingsUpdate(BaseModel):
    default_odds_format: Optional[str] = Field(default=None, pattern=ODDS_FORMAT_PATTERN)
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    bankroll: Optional[float] = Field(default=None, ge=0)
    kelly_multiplier: Optional[float] = Field(default=None, gt=0, le=1)
    preferred_locale: Optional[str] = Field(default=None, pattern=LOCALE_PATTERN)
    timezone: Optional[str] = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str | None) -> str | None:
        return _validate_iana_timezone(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    default_odds_format: str
    base_currency: str
    bankroll: float
    kelly_multiplier: float
    preferred_locale: str
    timezone: str
    is_admin: bool
    created_at: datetime

    # Billing / subscription (cached from Stripe)
    plan: str = "free"
    plan_currency: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_cancel_at_period_end: bool = False
    subscription_current_period_end: Optional[datetime] = None
    comp_pro_until: Optional[datetime] = None
    is_pro: bool = False


# ----------------------------- Billing / plans ---------------------------- #

class PriceOut(BaseModel):
    currency: str
    amount: float
    interval: str = "month"


class PricingOut(BaseModel):
    default_currency: str
    prices: list[PriceOut]


class PlanOut(BaseModel):
    """Current subscription state for the signed-in user."""
    plan: str = "free"
    billing_plan: str = "free"
    plan_currency: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_cancel_at_period_end: bool = False
    subscription_current_period_end: Optional[datetime] = None
    comp_pro_until: Optional[datetime] = None
    free_daily_bet_limit: int
    stripe_configured: bool = False
    # Bundled so the plan page works when extensions block /billing/pricing.
    pricing: Optional[PricingOut] = None


class CheckoutRequest(BaseModel):
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    locale: Optional[str] = Field(default=None, max_length=16)
    success_url: str
    cancel_url: str
    promotion_code: Optional[str] = None


class CheckoutSessionOut(BaseModel):
    id: str
    url: Optional[str] = None


class PortalSessionRequest(BaseModel):
    return_url: str


class PortalSessionOut(BaseModel):
    url: str


class PromoValidationOut(BaseModel):
    valid: bool
    code: str
    summary: Optional[str] = None
    terms: Optional[str] = None
    promo_type: Optional[str] = None
    free_months: Optional[int] = None
    percent_off: Optional[float] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    already_used: bool = False
    # Legacy Stripe coupon fields (kept for backward compatibility)
    amount_off: Optional[int] = None
    currency: Optional[str] = None
    duration: Optional[str] = None
    duration_in_months: Optional[int] = None


class PromoCodeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    promo_type: Literal["free_months", "percent_discount"]
    free_months: Optional[int] = Field(default=None, ge=1, le=24)
    percent_off: Optional[float] = Field(default=None, gt=0, le=100)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    active: bool = True
    description: Optional[str] = Field(default=None, max_length=512)


class PromoCodeUpdate(BaseModel):
    active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_redemptions: Optional[int] = Field(default=None, ge=1)
    description: Optional[str] = Field(default=None, max_length=512)


class PromoCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    code: str
    promo_type: str
    free_months: Optional[int]
    percent_off: Optional[float]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    max_redemptions: Optional[int]
    active: bool
    description: Optional[str]
    redemption_count: int = 0
    referral_count: int = 0
    created_at: datetime
    updated_at: datetime


class PromoRedemptionOut(BaseModel):
    user_id: str
    user_email: Optional[str] = None
    currency: Optional[str]
    referrer: Optional[str]
    redeemed_at: datetime


class PromoReferralOut(BaseModel):
    created_at: datetime
    path: str
    ip_address: Optional[str]
    referrer: Optional[str]
    country: Optional[str]
    is_bot: bool


class PromoCodeStatsOut(BaseModel):
    promo: PromoCodeOut
    redemptions: list[PromoRedemptionOut]
    referrals: list[PromoReferralOut]
    currencies: dict[str, int]


class BetUsageOut(BaseModel):
    """How many bets the user has entered today, against their plan's limit.

    `count`/`limit`/`remaining` track single bets; the `multiple_*` fields track
    multiple/parlay bets, which have their own separate daily allowance.
    """
    plan: str
    date: str
    count: int
    limit: Optional[int] = None  # null == unlimited (Pro)
    remaining: Optional[int] = None  # null == unlimited (Pro)
    multiple_count: int = 0
    multiple_limit: Optional[int] = None  # null == unlimited (Pro)
    multiple_remaining: Optional[int] = None  # null == unlimited (Pro)


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    prefix: str
    last_used_at: Optional[datetime]
    revoked: bool
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    # Full key is returned exactly once, at creation.
    api_key: str


# ----------------------------- Admin -------------------------------------- #

class AdminUserOut(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    base_currency: str
    preferred_locale: str
    created_at: datetime
    last_login_at: Optional[datetime]
    bet_count: int
    api_key_count: int
    plan: str = "free"
    comp_pro_until: Optional[datetime] = None
    is_pro: bool = False


class AdminCompProIn(BaseModel):
    """Set or clear complimentary Pro access. Pass null to revoke."""
    comp_pro_until: Optional[datetime] = None


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class AdminAddIn(BaseModel):
    email: EmailStr


class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_bets: int
    signups_today: int
    logins_today: int
    events_today: int
    landing_hits_today: int
    landing_unique_ips_today: int


class LandingTrackIn(BaseModel):
    path: str = "/"
    referrer: Optional[str] = None
    promo_code: Optional[str] = Field(default=None, max_length=64)


class LandingHitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    path: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    browser: Optional[str]
    country: Optional[str]
    is_bot: bool
    referrer: Optional[str]
    promo_code: Optional[str] = None
    created_at: datetime


class AppEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: Optional[str]
    user_email: Optional[str] = None
    event_type: str
    detail: Optional[str]
    ip_address: Optional[str]
    created_at: datetime


# -------------------------------- Bets ------------------------------------ #

class BetLegCreate(BaseModel):
    """One selection of a multiple / parlay bet."""
    event: str
    selection: str
    # Accept odds in any format; the bets service normalises to decimal.
    odds: float | str
    odds_format: Optional[str] = Field(default=None, pattern=ODDS_FORMAT_PATTERN)
    odds_denominator: Optional[float] = None  # for fractional when odds is the numerator


class BetLegOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    leg_index: int
    event: str
    selection: str
    odds_decimal: float
    odds_format: str


class BetBase(BaseModel):
    tournament: Optional[str] = None
    # event/selection/odds are optional on the wire because for a multiple the
    # service derives them from the legs. A model validator enforces that single
    # bets still provide them and multiples provide enough legs.
    event: Optional[str] = None
    selection: Optional[str] = None
    sport: str
    bet_type: str = "Win"
    side: Literal["back", "lay"] = "back"
    placed_at: Optional[datetime] = None
    event_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None

    # Multiple / parlay
    is_multiple: bool = False
    legs: Optional[list[BetLegCreate]] = None

    # Accept odds in any format; the bets service normalises to decimal.
    # A string is allowed so fractional odds can be sent as "11/8".
    odds: Optional[float | str] = None
    odds_format: Optional[str] = Field(default=None, pattern=ODDS_FORMAT_PATTERN)
    odds_denominator: Optional[float] = None  # for fractional when odds is the numerator

    stake: float = Field(gt=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    each_way: bool = False
    place_fraction: float = 0.25
    placed: bool = False
    free_bet: bool = False

    outcome: str = Field(default="pending")
    cash_out_amount: Optional[float] = None

    bet_model: Optional[str] = None
    model_implied_odds: Optional[float] = None
    personal_implied_odds: Optional[float] = None
    closing_odds: Optional[float] = None
    closing_odds_exchange: Optional[float] = None

    bookmaker: Optional[str] = None
    portal: Optional[str] = Field(default=None, pattern=PORTAL_PATTERN)
    exchange_commission_pct: float = 0.0

    tipster: Optional[str] = None
    bet_broker: Optional[str] = None
    notes: Optional[str] = None


class BetCreate(BetBase):
    @model_validator(mode="after")
    def _check_single_or_multiple(self) -> "BetCreate":
        if self.is_multiple:
            legs = self.legs or []
            if len(legs) < 2:
                raise ValueError("A multiple bet needs at least 2 selections")
            # Each-way and lay are not supported for multiples.
            if self.each_way:
                raise ValueError("Each-way is not supported for multiple bets")
            if self.free_bet:
                raise ValueError("Free bet is not supported for multiple bets")
            if self.side == "lay":
                raise ValueError("Lay is not supported for multiple bets")
        else:
            missing = [
                name
                for name, value in (
                    ("event", self.event),
                    ("selection", self.selection),
                    ("odds", self.odds),
                )
                if value is None or (isinstance(value, str) and not value.strip())
            ]
            if missing:
                raise ValueError(f"Missing required field(s): {', '.join(missing)}")
        return self


class BetUpdate(BaseModel):
    # Every field optional for PATCH-style edits.
    tournament: Optional[str] = None
    event: Optional[str] = None
    selection: Optional[str] = None
    sport: Optional[str] = None
    bet_type: Optional[str] = None
    side: Optional[Literal["back", "lay"]] = None
    placed_at: Optional[datetime] = None
    event_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    is_multiple: Optional[bool] = None
    legs: Optional[list[BetLegCreate]] = None
    odds: Optional[float | str] = None
    odds_format: Optional[str] = Field(default=None, pattern=ODDS_FORMAT_PATTERN)
    odds_denominator: Optional[float] = None
    stake: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = None
    each_way: Optional[bool] = None
    place_fraction: Optional[float] = None
    placed: Optional[bool] = None
    free_bet: Optional[bool] = None
    outcome: Optional[str] = None
    cash_out_amount: Optional[float] = None
    bet_model: Optional[str] = None
    model_implied_odds: Optional[float] = None
    personal_implied_odds: Optional[float] = None
    closing_odds: Optional[float] = None
    closing_odds_exchange: Optional[float] = None
    bookmaker: Optional[str] = None
    portal: Optional[str] = Field(default=None, pattern=PORTAL_PATTERN)
    exchange_commission_pct: Optional[float] = None
    tipster: Optional[str] = None
    bet_broker: Optional[str] = None
    notes: Optional[str] = None


class BetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    tournament: Optional[str] = None
    event: str
    selection: str
    sport: str
    bet_type: str
    side: str
    is_multiple: bool = False
    legs: list[BetLegOut] = []
    placed_at: datetime
    event_at: Optional[datetime] = None
    settled_at: datetime
    odds_decimal: float
    odds_format: str
    stake: float
    currency: str
    each_way: bool
    place_fraction: float
    placed: bool
    free_bet: bool = False
    outcome: str
    profit: float
    cash_out_amount: Optional[float]
    bet_model: Optional[str]
    model_implied_odds: Optional[float]
    personal_implied_odds: Optional[float]
    personal_edge_pct: Optional[float]
    model_edge_pct: Optional[float]
    kelly_stake: Optional[float]
    model_kelly_stake: Optional[float]
    closing_odds: Optional[float]
    closing_odds_exchange: Optional[float]
    bookmaker: Optional[str]
    portal: Optional[str]
    exchange_commission_pct: float
    tipster: Optional[str]
    bet_broker: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Derived, computed at serialisation time by the service.
    clv_pct: Optional[float] = None
    edge_pct: Optional[float] = None

    # Present when the owner has enabled a public share link.
    share_token: Optional[str] = None


class PublicBetOut(BaseModel):
    """Read-only bet payload for unauthenticated share links."""
    model_config = ConfigDict(from_attributes=True)
    sport: str
    bet_type: str
    tournament: Optional[str] = None
    event: str
    event_at: Optional[datetime] = None
    selection: str
    stake: float
    odds_decimal: float
    odds_format: str
    currency: str
    personal_implied_odds: Optional[float] = None
    notes: Optional[str] = None


class BetShareOut(BaseModel):
    share_token: str

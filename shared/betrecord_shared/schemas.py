"""Pydantic v2 schemas shared by the services."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ----------------------------- Auth / users ------------------------------- #

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class SettingsUpdate(BaseModel):
    display_name: Optional[str] = None
    default_odds_format: Optional[str] = Field(default=None, pattern="^(decimal|american|fractional)$")
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    bankroll: Optional[float] = Field(default=None, ge=0)
    kelly_multiplier: Optional[float] = Field(default=None, gt=0, le=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    display_name: Optional[str]
    default_odds_format: str
    base_currency: str
    bankroll: float
    kelly_multiplier: float
    is_admin: bool
    created_at: datetime


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


# -------------------------------- Bets ------------------------------------ #

class BetBase(BaseModel):
    event: str
    selection: str
    sport: str
    bet_type: str = "win"
    placed_at: Optional[datetime] = None

    # Accept odds in any format; the bets service normalises to decimal.
    # A string is allowed so fractional odds can be sent as "11/8".
    odds: float | str
    odds_format: Optional[str] = Field(default=None, pattern="^(decimal|american|fractional)$")
    odds_denominator: Optional[float] = None  # for fractional when odds is the numerator

    stake: float = Field(gt=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    each_way: bool = False
    place_fraction: float = 0.25
    placed: bool = False

    outcome: str = Field(default="pending")
    cash_out_amount: Optional[float] = None

    bet_model: Optional[str] = None
    model_implied_odds: Optional[float] = None
    personal_implied_odds: Optional[float] = None
    closing_odds: Optional[float] = None

    bookmaker: Optional[str] = None
    exchange: Optional[str] = None
    exchange_commission_pct: float = 0.0

    tipster: Optional[str] = None
    notes: Optional[str] = None


class BetCreate(BetBase):
    pass


class BetUpdate(BaseModel):
    # Every field optional for PATCH-style edits.
    event: Optional[str] = None
    selection: Optional[str] = None
    sport: Optional[str] = None
    bet_type: Optional[str] = None
    placed_at: Optional[datetime] = None
    odds: Optional[float | str] = None
    odds_format: Optional[str] = Field(default=None, pattern="^(decimal|american|fractional)$")
    odds_denominator: Optional[float] = None
    stake: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = None
    each_way: Optional[bool] = None
    place_fraction: Optional[float] = None
    placed: Optional[bool] = None
    outcome: Optional[str] = None
    cash_out_amount: Optional[float] = None
    bet_model: Optional[str] = None
    model_implied_odds: Optional[float] = None
    personal_implied_odds: Optional[float] = None
    closing_odds: Optional[float] = None
    bookmaker: Optional[str] = None
    exchange: Optional[str] = None
    exchange_commission_pct: Optional[float] = None
    tipster: Optional[str] = None
    notes: Optional[str] = None


class BetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event: str
    selection: str
    sport: str
    bet_type: str
    placed_at: datetime
    odds_decimal: float
    odds_format: str
    stake: float
    currency: str
    each_way: bool
    place_fraction: float
    placed: bool
    outcome: str
    profit: float
    cash_out_amount: Optional[float]
    bet_model: Optional[str]
    model_implied_odds: Optional[float]
    personal_implied_odds: Optional[float]
    kelly_stake: Optional[float]
    closing_odds: Optional[float]
    bookmaker: Optional[str]
    exchange: Optional[str]
    exchange_commission_pct: float
    tipster: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Derived, computed at serialisation time by the service.
    clv_pct: Optional[float] = None
    edge_pct: Optional[float] = None

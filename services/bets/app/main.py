"""Bets service — record, edit, delete, list, and settle bets.

On every write the canonical decimal odds, the net P/L (incl. exchange
commission and cash-out), and the Kelly stake recommendation are recomputed
from the bettor's settings, so the stored row is always self-consistent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from betrecord_shared import betting_math as bm
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db, init_db
from betrecord_shared.models import Bet, User
from betrecord_shared.schemas import BetCreate, BetOut, BetUpdate
from betrecord_shared.security import get_current_user

settings = get_settings()
app = FastAPI(title="mybetrecord · bets", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    if settings.environment != "production":
        init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "bets"}


# --------------------------- compute helpers ------------------------------ #

def _normalise_odds(value: float, fmt: str, denominator: Optional[float]) -> float:
    if fmt == "fractional" and denominator is not None:
        return bm.fractional_to_decimal(value, denominator)
    return bm.to_decimal(value, fmt)


def _recompute(bet: Bet, user: User) -> None:
    """Recompute profit + kelly stake from the bet's own fields and user bankroll."""
    bet.profit = bm.settle_profit(
        stake=bet.stake,
        decimal_odds=bet.odds_decimal,
        outcome=bet.outcome,
        each_way=bet.each_way,
        place_fraction=bet.place_fraction or 0.25,
        placed=bet.placed,
        exchange_commission_pct=bet.exchange_commission_pct or 0.0,
        cash_out_amount=bet.cash_out_amount,
    )
    # Kelly uses the bettor's own probability estimate (personal implied odds).
    if bet.personal_implied_odds and user.bankroll:
        p = bm.implied_probability(bet.personal_implied_odds)
        bet.kelly_stake = bm.kelly_stake(
            bet.odds_decimal, p, user.bankroll, user.kelly_multiplier or 1.0
        )
    else:
        bet.kelly_stake = None


def _serialise(bet: Bet) -> BetOut:
    out = BetOut.model_validate(bet)
    if bet.closing_odds:
        out.clv_pct = bm.closing_line_value(bet.odds_decimal, bet.closing_odds)
    if bet.personal_implied_odds:
        p = bm.implied_probability(bet.personal_implied_odds)
        out.edge_pct = round(bm.edge(bet.odds_decimal, p) * 100.0, 2)
    return out


# -------------------------------- routes ---------------------------------- #

@app.get("/bets/sports", response_model=list[str])
def sports_used(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct sports the user has entered before, for the entry dropdown."""
    rows = db.scalars(
        select(distinct(Bet.sport)).where(Bet.user_id == user.id).order_by(Bet.sport)
    ).all()
    return [s for s in rows if s]


@app.get("/bets", response_model=list[BetOut])
def list_bets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sport: Optional[str] = None,
    outcome: Optional[str] = None,
    bet_type: Optional[str] = None,
    tipster: Optional[str] = None,
    bookmaker: Optional[str] = None,
    exchange: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(default=200, le=1000),
    offset: int = 0,
):
    stmt = select(Bet).where(Bet.user_id == user.id)
    if sport:
        stmt = stmt.where(Bet.sport == sport)
    if outcome:
        stmt = stmt.where(Bet.outcome == outcome)
    if bet_type:
        stmt = stmt.where(Bet.bet_type == bet_type)
    if tipster:
        stmt = stmt.where(Bet.tipster == tipster)
    if bookmaker:
        stmt = stmt.where(Bet.bookmaker == bookmaker)
    if exchange:
        stmt = stmt.where(Bet.exchange == exchange)
    if date_from:
        stmt = stmt.where(Bet.placed_at >= date_from)
    if date_to:
        stmt = stmt.where(Bet.placed_at <= date_to)
    stmt = stmt.order_by(Bet.placed_at.desc()).limit(limit).offset(offset)
    return [_serialise(b) for b in db.scalars(stmt).all()]


@app.post("/bets", response_model=BetOut, status_code=201)
def create_bet(
    payload: BetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BetOut:
    odds_decimal = _normalise_odds(payload.odds, payload.odds_format, payload.odds_denominator)
    if odds_decimal <= 1.0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Decimal odds must exceed 1.0")

    bet = Bet(
        user_id=user.id,
        event=payload.event,
        selection=payload.selection,
        sport=payload.sport,
        bet_type=payload.bet_type,
        placed_at=payload.placed_at or datetime.now(timezone.utc),
        odds_decimal=odds_decimal,
        odds_format=payload.odds_format,
        stake=payload.stake,
        currency=(payload.currency or user.base_currency).upper(),
        each_way=payload.each_way,
        place_fraction=payload.place_fraction,
        placed=payload.placed,
        outcome=payload.outcome or "pending",
        cash_out_amount=payload.cash_out_amount,
        bet_model=payload.bet_model,
        model_implied_odds=payload.model_implied_odds,
        personal_implied_odds=payload.personal_implied_odds,
        closing_odds=payload.closing_odds,
        bookmaker=payload.bookmaker,
        exchange=payload.exchange,
        exchange_commission_pct=payload.exchange_commission_pct or 0.0,
        tipster=payload.tipster,
        notes=payload.notes,
    )
    _recompute(bet, user)
    db.add(bet)
    db.commit()
    db.refresh(bet)
    return _serialise(bet)


@app.get("/bets/{bet_id}", response_model=BetOut)
def get_bet(bet_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bet = db.get(Bet, bet_id)
    if not bet or bet.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    return _serialise(bet)


@app.patch("/bets/{bet_id}", response_model=BetOut)
def update_bet(
    bet_id: str,
    payload: BetUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BetOut:
    bet = db.get(Bet, bet_id)
    if not bet or bet.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")

    data = payload.model_dump(exclude_unset=True)

    # Odds need normalisation if any odds field changed.
    if "odds" in data or "odds_format" in data or "odds_denominator" in data:
        new_value = data.get("odds", bet.odds_decimal)
        new_fmt = data.get("odds_format", bet.odds_format)
        new_den = data.get("odds_denominator")
        bet.odds_decimal = _normalise_odds(new_value, new_fmt, new_den)
        bet.odds_format = new_fmt

    for field in (
        "event", "selection", "sport", "bet_type", "placed_at", "stake", "currency",
        "each_way", "place_fraction", "placed", "outcome", "cash_out_amount",
        "bet_model", "model_implied_odds", "personal_implied_odds", "closing_odds",
        "bookmaker", "exchange", "exchange_commission_pct", "tipster", "notes",
    ):
        if field in data:
            value = data[field]
            if field == "currency" and value:
                value = value.upper()
            setattr(bet, field, value)

    _recompute(bet, user)
    db.commit()
    db.refresh(bet)
    return _serialise(bet)


@app.delete("/bets/{bet_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_bet(bet_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    bet = db.get(Bet, bet_id)
    if not bet or bet.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    db.delete(bet)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

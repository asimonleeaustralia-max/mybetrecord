"""Bankroll helpers — starting bankroll plus settled P/L in a given currency."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import betting_math as bm
from .models import Bet, User


def is_ledger_settled(bet: Bet) -> bool:
    """True when the bet contributes to bankroll / ledger totals."""
    if bet.cash_out_amount is not None:
        return True
    return (bet.outcome or bm.PENDING).lower() != bm.PENDING


def current_bankroll(starting: float, settled_profit: float) -> float:
    """Current bankroll = starting bankroll + settled profit/loss."""
    return round(float(starting or 0.0) + float(settled_profit or 0.0), 2)


def settled_profit(db: Session, user_id: str, currency: str) -> float:
    """Sum of P/L on settled bets in one currency (pending excluded unless cashed out)."""
    total = db.scalar(
        select(func.coalesce(func.sum(Bet.profit), 0.0))
        .where(Bet.user_id == user_id)
        .where(Bet.currency == currency.upper())
        .where(
            or_(
                Bet.outcome != bm.PENDING,
                Bet.cash_out_amount.isnot(None),
            )
        )
    )
    return float(total or 0.0)


def effective_bankroll(db: Session, user: User, bet: Bet | None = None) -> float:
    """Current bankroll for Kelly, including an in-flight bet not yet committed."""
    base = user.base_currency or "GBP"
    stmt = (
        select(func.coalesce(func.sum(Bet.profit), 0.0))
        .where(Bet.user_id == user.id)
        .where(Bet.currency == base.upper())
        .where(
            or_(
                Bet.outcome != bm.PENDING,
                Bet.cash_out_amount.isnot(None),
            )
        )
    )
    if bet and bet.id:
        stmt = stmt.where(Bet.id != bet.id)
    other = float(db.scalar(stmt) or 0.0)
    this = _bet_contribution(bet) if bet and _bet_in_currency(bet, base) else 0.0
    return current_bankroll(user.bankroll or 0.0, other + this)


def _bet_in_currency(bet: Bet, currency: str) -> bool:
    return (bet.currency or currency).upper() == currency.upper()


def _bet_contribution(bet: Bet) -> float:
    if not is_ledger_settled(bet):
        return 0.0
    return float(bet.profit or 0.0)

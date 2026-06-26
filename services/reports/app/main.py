"""Reports service — analytics over a bettor's settled bets.

Read-only against the bets table. Provides the headline metrics (ROI, yield,
strike rate, profit), time series for the equity curve, breakdowns by sport /
tipster / bet type, and CSV + Excel exports of the filtered record.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from betrecord_shared import betting_math as bm
from betrecord_shared.bankroll import current_bankroll, settled_profit
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db
from betrecord_shared.models import Bet, User
from betrecord_shared.schemas import BetOut
from betrecord_shared.security import get_current_user

settings = get_settings()
app = FastAPI(title="mybetrecord · reports", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "reports"}


# ----------------------------- filtering ---------------------------------- #

def _filtered(db: Session, user_id: str, f: dict):
    stmt = select(Bet).where(Bet.user_id == user_id)
    if f.get("sport"):
        stmt = stmt.where(Bet.sport == f["sport"])
    if f.get("bet_type"):
        stmt = stmt.where(Bet.bet_type == f["bet_type"])
    if f.get("tipster"):
        stmt = stmt.where(Bet.tipster == f["tipster"])
    if f.get("bookmaker"):
        stmt = stmt.where(Bet.bookmaker == f["bookmaker"])
    if f.get("outcome"):
        stmt = stmt.where(Bet.outcome == f["outcome"])
    if f.get("currency"):
        stmt = stmt.where(Bet.currency == f["currency"])
    if f.get("date_from"):
        stmt = stmt.where(Bet.placed_at >= f["date_from"])
    if f.get("date_to"):
        stmt = stmt.where(Bet.placed_at <= f["date_to"])
    return db.scalars(stmt.order_by(Bet.placed_at.asc())).all()


def _dominant_currency(db: Session, user_id: str) -> Optional[str]:
    """Currency the user has recorded the most bets in (count; ties → alphabetical)."""
    rows = db.scalars(select(Bet.currency).where(Bet.user_id == user_id)).all()
    if not rows:
        return None
    counts = Counter((c or "GBP").upper() for c in rows)
    return max(counts, key=lambda k: (counts[k], k))


def _common_filters(
    sport: Optional[str] = None,
    bet_type: Optional[str] = None,
    tipster: Optional[str] = None,
    bookmaker: Optional[str] = None,
    outcome: Optional[str] = None,
    currency: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    return {
        "sport": sport, "bet_type": bet_type, "tipster": tipster,
        "bookmaker": bookmaker, "outcome": outcome,
        "currency": currency.upper() if currency else None,
        "date_from": date_from, "date_to": date_to,
    }


# ------------------------------- summary ---------------------------------- #

def _metrics_row(bet: Bet) -> dict:
    return {
        "stake": bet.stake,
        "profit": bet.profit,
        "outcome": bet.outcome,
        "cash_out_amount": bet.cash_out_amount,
        "side": bet.side or bm.BACK,
        "decimal_odds": bet.odds_decimal,
    }


@app.get("/reports/summary")
def summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
    use_primary_currency: bool = False,
):
    filters = dict(f)
    display_currency = filters.get("currency")
    if use_primary_currency and not display_currency:
        display_currency = _dominant_currency(db, user.id) or user.base_currency
        filters["currency"] = display_currency
    bets = _filtered(db, user.id, filters)
    rows = [_metrics_row(b) for b in bets]
    metrics = bm.portfolio_metrics(rows)
    base = (user.base_currency or "GBP").upper()
    if display_currency and display_currency.upper() == base:
        metrics["bankroll"] = current_bankroll(user.bankroll, metrics["profit"])
        metrics["roi_vs_bankroll_pct"] = bm.roi_vs_bankroll(metrics["profit"], user.bankroll)
    else:
        pl = settled_profit(db, user.id, base)
        metrics["bankroll"] = current_bankroll(user.bankroll, pl)
        metrics["roi_vs_bankroll_pct"] = bm.roi_vs_bankroll(pl, user.bankroll)
    metrics["base_currency"] = user.base_currency
    metrics["currency"] = display_currency
    metrics["total_bets"] = len(bets)
    return metrics


@app.get("/reports/equity-curve")
def equity_curve(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    """Cumulative profit over time — the equity curve for the charts page."""
    bets = [
        b for b in _filtered(db, user.id, f)
        if b.outcome not in ("pending",) or b.cash_out_amount is not None
    ]
    points = []
    running = 0.0
    for b in bets:
        running += b.profit
        points.append({
            "date": b.placed_at.isoformat(),
            "profit": round(b.profit, 2),
            "cumulative": round(running, 2),
        })
    return points


@app.get("/reports/breakdown")
def breakdown(
    dimension: str = Query(default="sport", pattern="^(sport|tipster|bet_type|bookmaker)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    """Profit / yield / strike rate grouped by a chosen dimension."""
    bets = _filtered(db, user.id, f)
    groups: dict[str, list] = defaultdict(list)
    for b in bets:
        key = getattr(b, dimension) or "—"
        groups[key].append(_metrics_row(b))
    result = []
    for key, rows in groups.items():
        m = bm.portfolio_metrics(rows)
        result.append({"key": key, **m})
    result.sort(key=lambda r: r["profit"], reverse=True)
    return result


# ------------------------------- exports ---------------------------------- #

_EXPORT_COLUMNS = [
    ("placed_at", "Date/Time placed"),
    ("settled_at", "Date/Time settled"),
    ("sport", "Sport"),
    ("tournament", "Tournament"),
    ("event", "Event"),
    ("event_at", "Event date/time"),
    ("selection", "Selection"),
    ("bet_type", "Bet type"),
    ("side", "Side"),
    ("odds_decimal", "Odds (decimal)"),
    ("stake", "Stake"),
    ("currency", "Currency"),
    ("outcome", "Result"),
    ("profit", "P/L"),
    ("cash_out_amount", "Cash out"),
    ("bet_model", "Model"),
    ("model_implied_odds", "Model odds"),
    ("personal_implied_odds", "Personal odds"),
    ("personal_edge_pct", "Personal edge %"),
    ("model_edge_pct", "Model edge %"),
    ("kelly_stake", "Personal Kelly stake"),
    ("model_kelly_stake", "Model Kelly stake"),
    ("closing_odds", "Closing odds bookmaker"),
    ("closing_odds_exchange", "Closing odds exchange"),
    ("bookmaker", "Bookmaker"),
    ("portal", "Portal"),
    ("exchange_commission_pct", "Winnings deduction %"),
    ("tipster", "Tipster"),
    ("notes", "Notes"),
]


def _value(bet: Bet, attr: str):
    v = getattr(bet, attr)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _serialise(bet: Bet) -> BetOut:
    out = BetOut.model_validate(bet)
    if bet.closing_odds:
        out.clv_pct = bm.closing_line_value(bet.odds_decimal, bet.closing_odds)
    out.edge_pct = bet.personal_edge_pct
    return out


@app.get("/reports/export.csv")
def export_csv(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    bets = _filtered(db, user.id, f)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _, label in _EXPORT_COLUMNS])
    for b in bets:
        writer.writerow([_value(b, attr) for attr, _ in _EXPORT_COLUMNS])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mybetrecord.csv"},
    )


@app.get("/reports/export.json")
def export_json(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    bets = _filtered(db, user.id, f)
    payload = [_serialise(b).model_dump(mode="json") for b in bets]
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=mybetrecord.json"},
    )


@app.get("/reports/export.xlsx")
def export_xlsx(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    bets = _filtered(db, user.id, f)
    wb = Workbook()
    ws = wb.active
    ws.title = "Bet record"
    ws.append([label for _, label in _EXPORT_COLUMNS])
    for b in bets:
        ws.append([_value(b, attr) for attr, _ in _EXPORT_COLUMNS])

    # Summary sheet.
    rows = [_metrics_row(b) for b in bets]
    m = bm.portfolio_metrics(rows)
    s = wb.create_sheet("Summary")
    s.append(["Metric", "Value"])
    s.append(["Profit/Loss", m["profit"]])
    s.append(["Turnover", m["turnover"]])
    s.append(["Yield %", m["yield_pct"]])
    s.append(["ROI %", m["roi_pct"]])
    s.append(["Strike rate %", m["strike_rate_pct"]])
    s.append(["Settled bets", m["settled_bets"]])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=mybetrecord.xlsx"},
    )

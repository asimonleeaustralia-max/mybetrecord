"""Reports service — analytics over a bettor's settled bets.

Read-only against the bets table. Provides the headline metrics (ROI, yield,
strike rate, profit), time series for the equity curve, breakdowns by sport /
tipster / bet type, and CSV + Excel exports of the filtered record.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from betrecord_shared import betting_math as bm
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db
from betrecord_shared.models import Bet, User
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
    if f.get("exchange"):
        stmt = stmt.where(Bet.exchange == f["exchange"])
    if f.get("outcome"):
        stmt = stmt.where(Bet.outcome == f["outcome"])
    if f.get("date_from"):
        stmt = stmt.where(Bet.placed_at >= f["date_from"])
    if f.get("date_to"):
        stmt = stmt.where(Bet.placed_at <= f["date_to"])
    return db.scalars(stmt.order_by(Bet.placed_at.asc())).all()


def _common_filters(
    sport: Optional[str] = None,
    bet_type: Optional[str] = None,
    tipster: Optional[str] = None,
    exchange: Optional[str] = None,
    outcome: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    return {
        "sport": sport, "bet_type": bet_type, "tipster": tipster,
        "exchange": exchange, "outcome": outcome,
        "date_from": date_from, "date_to": date_to,
    }


# ------------------------------- summary ---------------------------------- #

@app.get("/reports/summary")
def summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    bets = _filtered(db, user.id, f)
    rows = [{"stake": b.stake, "profit": b.profit, "outcome": b.outcome} for b in bets]
    metrics = bm.portfolio_metrics(rows)
    metrics["roi_vs_bankroll_pct"] = bm.roi_vs_bankroll(metrics["profit"], user.bankroll)
    metrics["base_currency"] = user.base_currency
    metrics["bankroll"] = user.bankroll
    metrics["total_bets"] = len(bets)
    return metrics


@app.get("/reports/equity-curve")
def equity_curve(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    """Cumulative profit over time — the equity curve for the charts page."""
    bets = [b for b in _filtered(db, user.id, f) if b.outcome not in ("pending",)]
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
    dimension: str = Query(default="sport", pattern="^(sport|tipster|bet_type|exchange)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    f: dict = Depends(_common_filters),
):
    """Profit / yield / strike rate grouped by a chosen dimension."""
    bets = _filtered(db, user.id, f)
    groups: dict[str, list] = defaultdict(list)
    for b in bets:
        key = getattr(b, dimension) or "—"
        groups[key].append({"stake": b.stake, "profit": b.profit, "outcome": b.outcome})
    result = []
    for key, rows in groups.items():
        m = bm.portfolio_metrics(rows)
        result.append({"key": key, **m})
    result.sort(key=lambda r: r["profit"], reverse=True)
    return result


# ------------------------------- exports ---------------------------------- #

_EXPORT_COLUMNS = [
    ("placed_at", "Date/Time"),
    ("sport", "Sport"),
    ("event", "Event"),
    ("selection", "Selection"),
    ("bet_type", "Bet type"),
    ("odds_decimal", "Odds (decimal)"),
    ("stake", "Stake"),
    ("currency", "Currency"),
    ("outcome", "Result"),
    ("profit", "P/L"),
    ("cash_out_amount", "Cash out"),
    ("bet_model", "Model"),
    ("model_implied_odds", "Model odds"),
    ("personal_implied_odds", "Personal odds"),
    ("kelly_stake", "Kelly stake"),
    ("closing_odds", "Closing odds"),
    ("exchange", "Exchange"),
    ("exchange_commission_pct", "Commission %"),
    ("tipster", "Tipster"),
    ("notes", "Notes"),
]


def _value(bet: Bet, attr: str):
    v = getattr(bet, attr)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


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
    rows = [{"stake": b.stake, "profit": b.profit, "outcome": b.outcome} for b in bets]
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

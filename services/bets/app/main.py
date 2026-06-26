"""Bets service — record, edit, delete, list, and settle bets.

On every write the canonical decimal odds, the net P/L (incl. winnings
deductions and cash-out), and the Kelly stake recommendation are recomputed
from the bettor's settings, so the stored row is always self-consistent.
"""

from __future__ import annotations

import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import html as html_module

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, Response
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from betrecord_shared import betting_math as bm
from betrecord_shared.bankroll import effective_bankroll
from betrecord_shared.config import get_settings
from betrecord_shared.database import get_db, init_db
from betrecord_shared.models import Bet, BetLeg, User
from betrecord_shared.schemas import (
    BetCreate,
    BetLegCreate,
    BetOut,
    BetShareOut,
    BetUpdate,
    BetUsageOut,
    PublicBetOut,
)
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


# --------------------------- multiple / parlay ---------------------------- #

# (event, selection, decimal_odds, odds_format) for one leg.
LegSpec = tuple[str, str, float, str]


def _build_leg_specs(legs: Optional[list[BetLegCreate]], default_fmt: str) -> list[LegSpec]:
    """Validate and normalise the legs of a multiple into decimal-odds specs."""
    count = len(legs or [])
    lo, hi = settings.min_parlay_legs, settings.max_parlay_legs
    if not (lo <= count <= hi):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"A multiple must have between {lo} and {hi} selections",
        )
    specs: list[LegSpec] = []
    for leg in legs or []:
        fmt = leg.odds_format or default_fmt
        odds_decimal = _normalise_odds(leg.odds, fmt, leg.odds_denominator)
        if odds_decimal <= 1.0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Each leg's decimal odds must exceed 1.0",
            )
        specs.append((leg.event.strip(), leg.selection.strip(), odds_decimal, fmt))
    return specs


def _multiple_summary(leg_specs: list[LegSpec]) -> tuple[str, str, float]:
    """Parent event label, selection summary, and combined decimal odds."""
    event = f"{len(leg_specs)}-leg multiple"
    selection = " / ".join(s for (_, s, _, _) in leg_specs)[:255]
    combined = bm.parlay_decimal_odds([d for (_, _, d, _) in leg_specs])
    return event, selection, combined


def _multiple_bet_type(bet_type: Optional[str]) -> str:
    """Keep an explicit parlay label, else default the generic 'Win' to 'Multiple'."""
    value = (bet_type or "").strip()
    if value and value.lower() != "win":
        return value
    return "Multiple"


def _leg_models(leg_specs: list[LegSpec]) -> list[BetLeg]:
    return [
        BetLeg(leg_index=i, event=e, selection=s, odds_decimal=d, odds_format=f)
        for i, (e, s, d, f) in enumerate(leg_specs)
    ]


def _sync_each_way_fields(bet: Bet) -> None:
    """Keep placed flag and outcome consistent for each-way bets."""
    outcome = (bet.outcome or bm.PENDING).lower()
    if not bet.each_way:
        bet.placed = False
        return
    # Legacy: placed=true with outcome=loss → normalize to placed outcome.
    if bet.placed and outcome == bm.LOSS:
        bet.outcome = bm.PLACED
        outcome = bm.PLACED
    if outcome == bm.WIN or outcome == bm.PLACED:
        bet.placed = True
    elif outcome == bm.LOSS:
        bet.placed = False
    else:
        bet.placed = False


def _validate_side_fields(side: str, each_way: bool) -> None:
    if (side or bm.BACK).lower() == bm.LAY and each_way:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Each-way bets are not supported for lay bets",
        )


def _recompute(bet: Bet, user: User, db: Session) -> None:
    """Recompute profit + kelly stake from the bet's own fields and user bankroll."""
    _sync_each_way_fields(bet)
    # Cash-out amount always drives stored P/L when set, overriding win/loss outcome math.
    bet.profit = bm.settle_profit(
        stake=bet.stake,
        decimal_odds=bet.odds_decimal,
        outcome=bet.outcome,
        each_way=bet.each_way,
        place_fraction=bet.place_fraction or 0.25,
        placed=bet.placed,
        exchange_commission_pct=bet.exchange_commission_pct or 0.0,
        cash_out_amount=bet.cash_out_amount,
        side=bet.side or bm.BACK,
    )
    if (bet.side or bm.BACK).lower() == bm.LAY:
        bet.personal_edge_pct = None
        bet.kelly_stake = None
        bet.model_edge_pct = None
        bet.model_kelly_stake = None
        return

    multiplier = user.kelly_multiplier or 1.0
    bankroll = effective_bankroll(db, user, bet)

    if bet.personal_implied_odds and bet.personal_implied_odds > 1.0:
        p = bm.implied_probability(bet.personal_implied_odds)
        bet.personal_edge_pct = bm.edge_pct_from_implied(bet.odds_decimal, bet.personal_implied_odds)
        bet.kelly_stake = (
            bm.kelly_stake(bet.odds_decimal, p, bankroll, multiplier) if bankroll else None
        )
    else:
        bet.personal_edge_pct = None
        bet.kelly_stake = None

    if bet.model_implied_odds and bet.model_implied_odds > 1.0:
        p = bm.implied_probability(bet.model_implied_odds)
        bet.model_edge_pct = bm.edge_pct_from_implied(bet.odds_decimal, bet.model_implied_odds)
        bet.model_kelly_stake = (
            bm.kelly_stake(bet.odds_decimal, p, bankroll, multiplier) if bankroll else None
        )
    else:
        bet.model_edge_pct = None
        bet.model_kelly_stake = None


def _serialise(bet: Bet) -> BetOut:
    out = BetOut.model_validate(bet)
    if bet.closing_odds:
        out.clv_pct = bm.closing_line_value(bet.odds_decimal, bet.closing_odds)
    out.edge_pct = bet.personal_edge_pct
    out.share_token = bet.share_token
    return out


def _serialise_public(bet: Bet) -> PublicBetOut:
    return PublicBetOut.model_validate(bet)


def _format_share_event_at(event_at: datetime | None) -> str | None:
    if not event_at:
        return None
    if event_at.tzinfo is None:
        event_at = event_at.replace(tzinfo=timezone.utc)
    return event_at.strftime("%d %b %Y %H:%M UTC")


def _format_share_personal_odds(bet: Bet) -> str | None:
    if bet.personal_implied_odds is None:
        return None
    return f"{bet.personal_implied_odds:.2f}"


def _share_optional_row(
    label: str,
    value: str | None,
    esc,
    *,
    num: bool = False,
    notes: bool = False,
) -> str:
    if not value:
        return ""
    cls = "num" if num else ""
    if notes:
        cls = (cls + " share-detail__notes").strip()
    class_attr = f' class="{cls}"' if cls else ""
    return f'<div class="share-detail__row"><dt>{esc(label)}</dt><dd{class_attr}>{esc(value)}</dd></div>'


def _format_share_odds(bet: Bet) -> str:
    if bet.odds_format == "american":
        dec = bet.odds_decimal
        if dec >= 2.0:
            return f"+{round((dec - 1) * 100)}"
        return str(round(-100 / (dec - 1)))
    if bet.odds_format == "fractional":
        num = round((bet.odds_decimal - 1) * 100)
        return f"{num}/100"
    return f"{bet.odds_decimal:.2f}"


def _share_page_html(bet: Bet, token: str, base_url: str = "https://mybetrecord.com") -> str:
    title = f"{bet.selection} — {bet.event}"
    og_title = html_module.escape(f"{bet.selection} @ {bet.event} — mybetrecord")
    og_desc = html_module.escape(
        f"{bet.sport} · {bet.bet_type} · stake {bet.stake:g} {bet.currency} @ {_format_share_odds(bet)}"
    )
    share_url = f"{base_url}/share/{token}"
    esc = html_module.escape
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex, nofollow" />
  <title>{esc(title)} — mybetrecord</title>
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{og_title}" />
  <meta property="og:description" content="{og_desc}" />
  <meta property="og:url" content="{esc(share_url)}" />
  <meta property="og:image" content="{base_url}/og-default.svg" />
  <meta name="twitter:card" content="summary" />
  <link rel="stylesheet" href="/app/styles.css" />
</head>
<body>
  <section class="share-view">
    <div class="share-view__panel">
      <div class="wordmark wordmark--lg">my<span>bet</span>record</div>
      <p class="share-view__tag">Read-only view</p>
      <main id="shareMain">
        <article class="share-detail">
          <dl class="share-detail__list">
            <div class="share-detail__row"><dt>Sport</dt><dd>{esc(bet.sport)}</dd></div>
            <div class="share-detail__row"><dt>Bet type</dt><dd>{esc(bet.bet_type)}</dd></div>
            {_share_optional_row("Tournament", bet.tournament, esc)}
            <div class="share-detail__row"><dt>Event</dt><dd>{esc(bet.event)}</dd></div>
            {_share_optional_row("Event time", _format_share_event_at(bet.event_at), esc)}
            <div class="share-detail__row"><dt>Selection</dt><dd>{esc(bet.selection)}</dd></div>
            <div class="share-detail__row"><dt>Stake</dt><dd class="num">{bet.stake:g} {esc(bet.currency)}</dd></div>
            <div class="share-detail__row"><dt>Odds</dt><dd class="num">{esc(_format_share_odds(bet))}</dd></div>
            {_share_optional_row("Personal implied odds", _format_share_personal_odds(bet), esc, num=True)}
            {_share_optional_row("Notes", bet.notes, esc, notes=True)}
          </dl>
        </article>
      </main>
    </div>
  </section>
</body>
</html>"""


def _new_share_token(db: Session) -> str:
    """Generate a unique, URL-safe share token."""
    for _ in range(10):
        token = secrets.token_urlsafe(16)
        existing = db.scalar(select(Bet.id).where(Bet.share_token == token))
        if not existing:
            return token
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not create share link")


# --------------------------- free-plan limits ----------------------------- #

def _user_zone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _local_day_bounds(user: User) -> tuple[datetime, datetime, str]:
    """Start/end (UTC) of the user's current local day, plus the local date string."""
    zone = _user_zone(user)
    now_local = datetime.now(zone)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
        start_local.date().isoformat(),
    )


def _bets_entered_today(db: Session, user: User, *, is_multiple: Optional[bool] = None) -> int:
    start_utc, end_utc, _ = _local_day_bounds(user)
    stmt = (
        select(func.count())
        .select_from(Bet)
        .where(
            Bet.user_id == user.id,
            Bet.created_at >= start_utc,
            Bet.created_at < end_utc,
        )
    )
    if is_multiple is not None:
        stmt = stmt.where(Bet.is_multiple == is_multiple)
    return db.scalar(stmt) or 0


def _usage(db: Session, user: User) -> BetUsageOut:
    _, _, day = _local_day_bounds(user)
    single_count = _bets_entered_today(db, user, is_multiple=False)
    multiple_count = _bets_entered_today(db, user, is_multiple=True)
    if user.is_pro:
        return BetUsageOut(
            plan=user.plan or "free",
            date=day,
            count=single_count,
            limit=None,
            remaining=None,
            multiple_count=multiple_count,
            multiple_limit=None,
            multiple_remaining=None,
        )
    limit = settings.free_daily_bet_limit
    multiple_limit = settings.free_daily_multiple_limit
    return BetUsageOut(
        plan=user.plan or "free",
        date=day,
        count=single_count,
        limit=limit,
        remaining=max(0, limit - single_count),
        multiple_count=multiple_count,
        multiple_limit=multiple_limit,
        multiple_remaining=max(0, multiple_limit - multiple_count),
    )


def _enforce_daily_limit(db: Session, user: User, *, is_multiple: bool = False) -> None:
    """Free users get a separate daily allowance for single and multiple bets."""
    if user.is_pro:
        return
    if is_multiple:
        limit = settings.free_daily_multiple_limit
        if _bets_entered_today(db, user, is_multiple=True) >= limit:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                f"Free plan limit reached: you can enter up to {limit} multiple/parlay "
                "bets per day. Upgrade to Pro for unlimited bets.",
            )
        return
    limit = settings.free_daily_bet_limit
    if _bets_entered_today(db, user, is_multiple=False) >= limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Free plan limit reached: you can enter up to {limit} bets per day. "
            "Upgrade to Pro for unlimited bets.",
        )


# -------------------------------- routes ---------------------------------- #

@app.get("/bets/usage", response_model=BetUsageOut)
def bet_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BetUsageOut:
    """Today's bet count against the user's plan limit (null limit == unlimited)."""
    return _usage(db, user)

@app.get("/bets/sports", response_model=list[str])
def sports_used(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct sports the user has entered before, for the entry dropdown."""
    rows = db.scalars(
        select(distinct(Bet.sport)).where(Bet.user_id == user.id).order_by(Bet.sport)
    ).all()
    return [s for s in rows if s]


@app.get("/bets/bet-types", response_model=list[str])
def bet_types_used(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct bet types the user has entered before, for the entry dropdown."""
    rows = db.scalars(
        select(distinct(Bet.bet_type)).where(Bet.user_id == user.id).order_by(Bet.bet_type)
    ).all()
    return [t for t in rows if t]


@app.get("/bets/tipsters", response_model=list[str])
def tipsters_used(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Distinct tipsters the user has entered before, for report filters."""
    rows = db.scalars(
        select(distinct(Bet.tipster)).where(Bet.user_id == user.id).order_by(Bet.tipster)
    ).all()
    return [t for t in rows if t]


@app.get("/bets/currencies", response_model=list[str])
def currencies_used(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Currencies the user has bet in, most-used first (for report filters)."""
    rows = db.scalars(select(Bet.currency).where(Bet.user_id == user.id)).all()
    counts = Counter((c or "GBP").upper() for c in rows)
    return sorted(counts, key=lambda k: (-counts[k], k))


@app.get("/bets", response_model=list[BetOut])
def list_bets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sport: Optional[str] = None,
    outcome: Optional[str] = None,
    bet_type: Optional[str] = None,
    tipster: Optional[str] = None,
    bookmaker: Optional[str] = None,
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
    if date_from:
        stmt = stmt.where(Bet.placed_at >= date_from)
    if date_to:
        stmt = stmt.where(Bet.placed_at <= date_to)
    stmt = stmt.order_by(Bet.placed_at.desc()).limit(limit).offset(offset)
    return [_serialise(b) for b in db.scalars(stmt).all()]


@app.get("/bets/public/{share_token}", response_model=PublicBetOut)
def get_public_bet(share_token: str, db: Session = Depends(get_db)):
    """Read-only view of a bet via its share link. No authentication required."""
    bet = db.scalar(select(Bet).where(Bet.share_token == share_token))
    if not bet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    return _serialise_public(bet)


@app.get("/bets/share-page/{share_token}", response_class=HTMLResponse)
def share_page(share_token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Server-rendered share page with Open Graph tags (noindex)."""
    bet = db.scalar(select(Bet).where(Bet.share_token == share_token))
    if not bet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    return HTMLResponse(_share_page_html(bet, share_token))


@app.post("/bets/{bet_id}/share", response_model=BetShareOut)
def enable_bet_share(
    bet_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BetShareOut:
    bet = db.get(Bet, bet_id)
    if not bet or bet.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    if not bet.share_token:
        bet.share_token = _new_share_token(db)
        db.commit()
        db.refresh(bet)
    return BetShareOut(share_token=bet.share_token)


@app.delete("/bets/{bet_id}/share", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def disable_bet_share(
    bet_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    bet = db.get(Bet, bet_id)
    if not bet or bet.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bet not found")
    if bet.share_token:
        bet.share_token = None
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/bets", response_model=BetOut, status_code=201)
def create_bet(
    payload: BetCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BetOut:
    _enforce_daily_limit(db, user, is_multiple=payload.is_multiple)
    odds_format = payload.odds_format or user.default_odds_format or "decimal"

    legs: list[BetLeg] = []
    if payload.is_multiple:
        leg_specs = _build_leg_specs(payload.legs, odds_format)
        event, selection, odds_decimal = _multiple_summary(leg_specs)
        legs = _leg_models(leg_specs)
        bet_type = _multiple_bet_type(payload.bet_type)
        side = bm.BACK
        each_way = False
        stored_format = "decimal"  # combined odds are an inherently decimal product
    else:
        odds_decimal = _normalise_odds(payload.odds, odds_format, payload.odds_denominator)
        if odds_decimal <= 1.0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Decimal odds must exceed 1.0")
        _validate_side_fields(payload.side, payload.each_way)
        event = payload.event
        selection = payload.selection
        bet_type = payload.bet_type
        side = payload.side
        each_way = payload.each_way
        stored_format = odds_format

    bet = Bet(
        user_id=user.id,
        tournament=payload.tournament,
        event=event,
        selection=selection,
        sport=payload.sport,
        bet_type=bet_type,
        side=side,
        is_multiple=payload.is_multiple,
        placed_at=payload.placed_at or datetime.now(timezone.utc),
        event_at=payload.event_at,
        settled_at=payload.settled_at or datetime.now(timezone.utc),
        odds_decimal=odds_decimal,
        odds_format=stored_format,
        stake=payload.stake,
        currency=(payload.currency or user.base_currency).upper(),
        each_way=each_way,
        place_fraction=payload.place_fraction,
        placed=payload.placed,
        outcome=payload.outcome or "pending",
        cash_out_amount=payload.cash_out_amount,
        bet_model=payload.bet_model,
        model_implied_odds=payload.model_implied_odds,
        personal_implied_odds=payload.personal_implied_odds,
        closing_odds=payload.closing_odds,
        closing_odds_exchange=payload.closing_odds_exchange,
        bookmaker=payload.bookmaker,
        portal=payload.portal,
        exchange_commission_pct=payload.exchange_commission_pct or 0.0,
        tipster=payload.tipster,
        bet_broker=payload.bet_broker,
        notes=payload.notes,
    )
    bet.legs = legs
    _recompute(bet, user, db)
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
    prev_outcome = (bet.outcome or bm.PENDING).lower()

    target_multiple = payload.is_multiple if payload.is_multiple is not None else bet.is_multiple

    # Fields whose values are derived (multiples) or handled out of the loop.
    skip: set[str] = {"odds", "odds_format", "odds_denominator", "is_multiple", "legs"}

    if target_multiple:
        default_fmt = payload.odds_format or user.default_odds_format or "decimal"
        if payload.legs is not None:
            leg_specs = _build_leg_specs(payload.legs, default_fmt)
        elif bet.legs:
            leg_specs = [(l.event, l.selection, l.odds_decimal, l.odds_format) for l in bet.legs]
        else:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "A multiple bet requires at least 2 selections",
            )
        event, selection, odds_decimal = _multiple_summary(leg_specs)
        bet.is_multiple = True
        bet.event = event
        bet.selection = selection
        bet.odds_decimal = odds_decimal
        bet.odds_format = "decimal"
        bet.side = bm.BACK
        bet.each_way = False
        bet.placed = False
        bet.legs = _leg_models(leg_specs)
        # event/selection/side/each_way/placed are derived for multiples.
        skip |= {"event", "selection", "side", "each_way", "placed"}
        if "bet_type" in data:
            bet.bet_type = _multiple_bet_type(data["bet_type"])
            skip.add("bet_type")
        elif not bet.bet_type:
            bet.bet_type = "Multiple"
    else:
        bet.is_multiple = False
        if bet.legs:
            bet.legs = []  # dropping legs when converting a multiple back to a single
        # Odds need normalisation if any odds field changed.
        if "odds" in data or "odds_format" in data or "odds_denominator" in data:
            new_value = data.get("odds", bet.odds_decimal)
            new_fmt = data.get("odds_format", bet.odds_format)
            new_den = data.get("odds_denominator")
            bet.odds_decimal = _normalise_odds(new_value, new_fmt, new_den)
            bet.odds_format = new_fmt

    for field in (
        "tournament", "event", "selection", "sport", "bet_type", "side", "placed_at", "event_at", "settled_at", "stake", "currency",
        "each_way", "place_fraction", "placed", "outcome", "cash_out_amount",
        "bet_model", "model_implied_odds", "personal_implied_odds", "closing_odds", "closing_odds_exchange",
        "bookmaker", "portal", "exchange_commission_pct", "tipster", "bet_broker", "notes",
    ):
        if field in skip:
            continue
        if field in data:
            value = data[field]
            if field in ("placed_at", "settled_at") and value is None:
                value = datetime.now(timezone.utc)
            if field == "currency" and value:
                value = value.upper()
            setattr(bet, field, value)

    _validate_side_fields(bet.side or bm.BACK, bet.each_way)

    if "outcome" in data:
        new_outcome = (bet.outcome or bm.PENDING).lower()
        if prev_outcome == bm.PENDING and new_outcome != bm.PENDING and "settled_at" not in data:
            bet.settled_at = datetime.now(timezone.utc)

    _recompute(bet, user, db)
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

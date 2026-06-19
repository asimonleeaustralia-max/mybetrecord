"""
Pure betting math. No I/O, no framework imports — just numbers.

Everything here is deterministic and unit-testable. The services call into this
module so that "what is the P/L of this bet" has exactly one answer everywhere.

Odds vocabulary
---------------
- decimal odds (D): total return per unit staked, e.g. 2.50 returns 2.50 for 1 staked.
- american / moneyline (A): +150 means stake 100 to win 150; -200 means stake 200 to win 100.
- fractional (N/M): profit N for every M staked, e.g. 6/4.
- hong_kong (HK): profit per unit staked, e.g. 0.85 → decimal 1.85.
- malaysian / indonesian: signed profit per unit; +0.85 → 1.85, -0.85 → 2.176.
- implied probability (p): the probability the price corresponds to = 1 / D.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from math import isfinite
from typing import Iterable, Optional


# --------------------------------------------------------------------------- #
# Odds conversions — decimal is the canonical internal representation.
# --------------------------------------------------------------------------- #

def american_to_decimal(american: float) -> float:
    a = float(american)
    if a == 0:
        raise ValueError("American odds cannot be 0")
    if a > 0:
        return 1.0 + a / 100.0
    return 1.0 + 100.0 / abs(a)


def fractional_to_decimal(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ValueError("Fractional denominator cannot be 0")
    return 1.0 + float(numerator) / float(denominator)


def fractional_str_to_decimal(text: str) -> float:
    """Parse '6/4', '11/8', or a bare '2.5' into decimal odds."""
    text = text.strip()
    if "/" in text:
        num, _, den = text.partition("/")
        return fractional_to_decimal(float(num), float(den))
    return float(text)


def decimal_to_american(decimal_odds: float) -> int:
    d = float(decimal_odds)
    if d <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    if d >= 2.0:
        return round((d - 1.0) * 100.0)
    return round(-100.0 / (d - 1.0))


def decimal_to_fractional(decimal_odds: float, max_denominator: int = 100) -> str:
    d = float(decimal_odds)
    if d <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    frac = Fraction(d - 1.0).limit_denominator(max_denominator)
    return f"{frac.numerator}/{frac.denominator}"


def _parse_signed_float(value: float | str) -> float:
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise ValueError("Odds value is empty")
        return float(text.replace("+", ""))
    return float(value)


def hong_kong_to_decimal(hk: float | str) -> float:
    o = _parse_signed_float(hk)
    if o < 0:
        raise ValueError("Hong Kong odds cannot be negative")
    return 1.0 + o


def signed_asian_to_decimal(odds: float | str) -> float:
    """Malaysian and Indonesian odds share the same sign convention."""
    o = _parse_signed_float(odds)
    if o == 0:
        raise ValueError("Odds cannot be 0")
    return (1.0 + o) if o > 0 else (1.0 + 1.0 / abs(o))


def decimal_to_hong_kong(decimal_odds: float) -> float:
    d = float(decimal_odds)
    if d <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    return round(d - 1.0, 4)


def decimal_to_signed_asian(decimal_odds: float, *, positive_when_under_evens: bool) -> float:
    """Convert decimal odds to signed Asian display.

    Malaysian uses positive odds when decimal <= 2 (profit < stake).
    Indonesian uses positive odds when decimal >= 2 (profit >= stake).
    """
    d = float(decimal_odds)
    if d <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    if positive_when_under_evens:
        if d <= 2.0:
            return round(d - 1.0, 4)
        return round(-1.0 / (d - 1.0), 4)
    if d >= 2.0:
        return round(d - 1.0, 4)
    return round(-1.0 / (d - 1.0), 4)


def decimal_to_malaysian(decimal_odds: float) -> float:
    return decimal_to_signed_asian(decimal_odds, positive_when_under_evens=True)


def decimal_to_indonesian(decimal_odds: float) -> float:
    return decimal_to_signed_asian(decimal_odds, positive_when_under_evens=False)


def to_decimal(value: float | str, odds_format: str = "decimal",
               denominator: Optional[float] = None) -> float:
    """Normalise any supported input to decimal odds.

    odds_format: 'decimal' | 'american' | 'fractional' | 'hong_kong' |
                 'malaysian' | 'indonesian'
    For 'fractional' either pass value as 'N/M' string, or value=N with denominator=M.
    """
    fmt = (odds_format or "decimal").lower()
    if fmt == "decimal":
        return float(value)
    if fmt == "american":
        return american_to_decimal(_parse_signed_float(value))
    if fmt == "fractional":
        if isinstance(value, str):
            return fractional_str_to_decimal(value)
        if denominator is None:
            raise ValueError("Fractional odds need a denominator")
        return fractional_to_decimal(float(value), denominator)
    if fmt == "hong_kong":
        return hong_kong_to_decimal(value)
    if fmt == "malaysian":
        return signed_asian_to_decimal(value)
    if fmt == "indonesian":
        return signed_asian_to_decimal(value)
    raise ValueError(f"Unknown odds format: {odds_format}")


def implied_probability(decimal_odds: float) -> float:
    """Probability the price implies (includes the bookmaker's margin)."""
    d = float(decimal_odds)
    if d <= 0:
        raise ValueError("Decimal odds must be positive")
    return 1.0 / d


def decimal_from_probability(probability: float) -> float:
    if not (0.0 < probability < 1.0):
        raise ValueError("Probability must be strictly between 0 and 1")
    return 1.0 / probability


# --------------------------------------------------------------------------- #
# Kelly staking
# --------------------------------------------------------------------------- #

def kelly_fraction(decimal_odds: float, true_probability: float) -> float:
    """Fraction of bankroll to stake under the Kelly criterion.

    f* = (b*p - q) / b  where b = decimal_odds - 1, q = 1 - p.
    Returns 0 when there is no edge (never recommends a negative stake).
    """
    b = float(decimal_odds) - 1.0
    if b <= 0:
        return 0.0
    p = float(true_probability)
    q = 1.0 - p
    f = (b * p - q) / b
    return max(0.0, f)


def kelly_stake(decimal_odds: float, true_probability: float,
                bankroll: float, multiplier: float = 1.0) -> float:
    """Recommended stake. multiplier=0.5 gives half-Kelly, 0.25 quarter-Kelly."""
    f = kelly_fraction(decimal_odds, true_probability) * float(multiplier)
    return round(max(0.0, f) * float(bankroll), 2)


def edge(decimal_odds: float, personal_probability: float) -> float:
    """Expected value per unit staked: p*(D-1) - (1-p)."""
    d = float(decimal_odds)
    p = float(personal_probability)
    return p * (d - 1.0) - (1.0 - p)


def edge_pct_from_implied(decimal_odds: float, implied_odds_decimal: float) -> Optional[float]:
    """Edge as a percentage when the estimate is expressed as decimal implied odds."""
    implied = float(implied_odds_decimal)
    if implied <= 1.0:
        return None
    p = implied_probability(implied)
    return round(edge(decimal_odds, p) * 100.0, 2)


# --------------------------------------------------------------------------- #
# Settlement — profit / loss for a single bet.
# --------------------------------------------------------------------------- #

# Outcome constants
WIN = "win"
LOSS = "loss"
VOID = "void"
HALF_WIN = "half_win"     # Asian handicap / push-on-half
HALF_LOSS = "half_loss"
PENDING = "pending"
CASHED_OUT = "cashed_out"


def settle_profit(
    *,
    stake: float,
    decimal_odds: float,
    outcome: str,
    each_way: bool = False,
    place_fraction: float = 0.25,   # e.g. 1/4 odds for the place part
    placed: bool = False,           # did the each-way 'place' part win?
    exchange_commission_pct: float = 0.0,   # % deducted from net winnings
    cash_out_amount: Optional[float] = None,
) -> float:
    """Return profit/loss for one bet (negative = loss), net of winnings deductions.

    Notes
    -----
    * stake is the TOTAL staked. For an each-way bet that is the combined
      win + place stake; the unit stake is stake / 2.
    * winnings deductions apply only to net winnings, and only when the bet
      shows a profit (e.g. exchange commission).
    * a non-null cash_out_amount overrides outcome: P/L = cash_out - stake.
    """
    stake = float(stake)
    d = float(decimal_odds)

    if cash_out_amount is not None:
        return round(float(cash_out_amount) - stake, 2)

    outcome = (outcome or PENDING).lower()
    if outcome in (PENDING,):
        return 0.0
    if outcome == VOID:
        return 0.0

    if not each_way:
        if outcome in (WIN,):
            gross = stake * (d - 1.0)
        elif outcome in (HALF_WIN,):
            gross = 0.5 * stake * (d - 1.0)
        elif outcome in (HALF_LOSS,):
            gross = -0.5 * stake
        elif outcome in (LOSS,):
            gross = -stake
        else:
            gross = 0.0
    else:
        unit = stake / 2.0
        win_part = 0.0
        place_part = 0.0
        # Win part settles on the full result.
        if outcome == WIN:
            win_part = unit * (d - 1.0)
        else:
            win_part = -unit
        # Place part settles on whether it placed (a win implies a place).
        place_odds = 1.0 + (d - 1.0) * float(place_fraction)
        if placed or outcome == WIN:
            place_part = unit * (place_odds - 1.0)
        else:
            place_part = -unit
        gross = win_part + place_part

    commission = 0.0
    if gross > 0 and exchange_commission_pct:
        commission = gross * (float(exchange_commission_pct) / 100.0)
    return round(gross - commission, 2)


def returns_including_stake(stake: float, profit: float) -> float:
    """Total returned to the bettor (stake back + profit) for winners."""
    return round(float(stake) + float(profit), 2)


# --------------------------------------------------------------------------- #
# Closing line value — were you beating the closing price?
# --------------------------------------------------------------------------- #

def closing_line_value(taken_decimal: float, closing_decimal: float) -> Optional[float]:
    """CLV as a percentage. Positive means you got a better price than close."""
    if not closing_decimal or closing_decimal <= 1.0:
        return None
    return round((float(taken_decimal) / float(closing_decimal) - 1.0) * 100.0, 2)


# --------------------------------------------------------------------------- #
# Portfolio metrics over a collection of settled bets.
# --------------------------------------------------------------------------- #

def _q(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def portfolio_metrics(rows: Iterable[dict]) -> dict:
    """Aggregate ROI, yield, strike rate, profit and turnover.

    Each row is expected to expose: stake (float), profit (float),
    outcome (str), and optionally settled (bool). Pending/unsettled bets
    are excluded from strike-rate denominators but their stake still counts
    as committed turnover only once settled.

    Definitions used (and shown to users on the reports page):
      turnover     = sum of stakes on settled bets
      profit       = sum of P/L on settled bets
      yield        = profit / turnover            (return per unit staked)
      roi          = profit / turnover            (same basis; see note)
      strike_rate  = wins / settled bets
    """
    turnover = 0.0
    profit = 0.0
    settled = 0
    wins = 0
    losses = 0
    voids = 0

    for r in rows:
        outcome = (r.get("outcome") or PENDING).lower()
        if outcome in (PENDING,):
            continue
        stake = float(r.get("stake") or 0.0)
        pl = float(r.get("profit") or 0.0)
        turnover += stake
        profit += pl
        settled += 1
        if outcome in (WIN, HALF_WIN, CASHED_OUT) and pl > 0:
            wins += 1
        elif outcome == VOID:
            voids += 1
        elif pl < 0:
            losses += 1

    yield_pct = (profit / turnover * 100.0) if turnover else 0.0
    roi_pct = yield_pct  # identical basis; ROI-vs-bankroll is a separate view
    strike = (wins / settled * 100.0) if settled else 0.0

    return {
        "turnover": _q(turnover),
        "profit": _q(profit),
        "yield_pct": _q(yield_pct),
        "roi_pct": _q(roi_pct),
        "strike_rate_pct": _q(strike),
        "settled_bets": settled,
        "wins": wins,
        "losses": losses,
        "voids": voids,
    }


def roi_vs_bankroll(profit: float, bankroll: float) -> Optional[float]:
    if not bankroll:
        return None
    return _q(float(profit) / float(bankroll) * 100.0)

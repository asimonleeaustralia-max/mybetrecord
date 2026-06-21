"""Tests for the betting math — the part that must never be wrong."""

import math

import pytest

from betrecord_shared import betting_math as bm
from betrecord_shared.bankroll import current_bankroll


# ------------------------------ conversions ------------------------------ #

def test_american_to_decimal_positive():
    assert bm.american_to_decimal(150) == pytest.approx(2.5)

def test_american_to_decimal_negative():
    assert bm.american_to_decimal(-200) == pytest.approx(1.5)

def test_decimal_to_american_roundtrip():
    assert bm.decimal_to_american(2.5) == 150
    assert bm.decimal_to_american(1.5) == -200

def test_fractional():
    assert bm.fractional_str_to_decimal("6/4") == pytest.approx(2.5)
    assert bm.fractional_str_to_decimal("2.5") == pytest.approx(2.5)


def test_hong_kong_to_decimal():
    assert bm.hong_kong_to_decimal(0.85) == pytest.approx(1.85)
    assert bm.hong_kong_to_decimal("0.85") == pytest.approx(1.85)


def test_hong_kong_negative_rejected():
    with pytest.raises(ValueError):
        bm.hong_kong_to_decimal(-0.5)


def test_signed_asian_positive():
    assert bm.signed_asian_to_decimal(0.85) == pytest.approx(1.85)
    assert bm.signed_asian_to_decimal(1.5) == pytest.approx(2.5)
    assert bm.signed_asian_to_decimal("+0.85") == pytest.approx(1.85)


def test_signed_asian_negative():
    assert bm.signed_asian_to_decimal(-0.85) == pytest.approx(1 + 1 / 0.85)
    assert bm.signed_asian_to_decimal(-1.5) == pytest.approx(1 + 1 / 1.5)


def test_decimal_to_hong_kong():
    assert bm.decimal_to_hong_kong(1.85) == pytest.approx(0.85)


def test_decimal_to_signed_asian_roundtrip():
    assert bm.decimal_to_malaysian(1.85) == pytest.approx(0.85)
    assert bm.decimal_to_indonesian(2.5) == pytest.approx(1.5)
    neg_malay = bm.decimal_to_malaysian(1 + 1 / 0.85)
    assert neg_malay == pytest.approx(-0.85)
    neg_indo = bm.decimal_to_indonesian(1 + 1 / 1.5)
    assert neg_indo == pytest.approx(-1.5)


def test_to_decimal_asian_formats():
    assert bm.to_decimal(0.85, "hong_kong") == pytest.approx(1.85)
    assert bm.to_decimal(0.85, "malaysian") == pytest.approx(1.85)
    assert bm.to_decimal(-1.5, "indonesian") == pytest.approx(1 + 1 / 1.5)

def test_implied_probability():
    assert bm.implied_probability(2.0) == pytest.approx(0.5)
    assert bm.implied_probability(4.0) == pytest.approx(0.25)


# -------------------------------- kelly ---------------------------------- #

def test_kelly_fraction_with_edge():
    # Even-money price, 60% true prob -> f = (1*0.6 - 0.4)/1 = 0.2
    assert bm.kelly_fraction(2.0, 0.6) == pytest.approx(0.2)

def test_kelly_no_edge_is_zero():
    assert bm.kelly_fraction(2.0, 0.4) == 0.0

def test_kelly_stake_half():
    assert bm.kelly_stake(2.0, 0.6, bankroll=1000, multiplier=0.5) == pytest.approx(100.0)


def test_edge_pct_from_implied():
    assert bm.edge_pct_from_implied(2.5, 2.1) == pytest.approx(19.05, abs=0.1)


# ------------------------------ settlement ------------------------------- #

def test_win_profit():
    assert bm.settle_profit(stake=100, decimal_odds=2.5, outcome="win") == pytest.approx(150.0)

def test_loss_profit():
    assert bm.settle_profit(stake=100, decimal_odds=2.5, outcome="loss") == pytest.approx(-100.0)

def test_void_profit():
    assert bm.settle_profit(stake=100, decimal_odds=2.5, outcome="void") == 0.0

def test_exchange_commission_on_winner():
    # Profit 150, 5% commission -> 142.5
    pl = bm.settle_profit(stake=100, decimal_odds=2.5, outcome="win", exchange_commission_pct=5)
    assert pl == pytest.approx(142.5)


def test_effective_decimal_odds():
    eff = bm.effective_decimal_odds(2.5, 5)
    assert eff == pytest.approx(2.425)
    assert bm.effective_decimal_odds(2.5, 0) is None
    assert bm.effective_decimal_odds(1.0, 5) is None
    pl = bm.settle_profit(stake=100, decimal_odds=2.5, outcome="win", exchange_commission_pct=5)
    assert pl == pytest.approx(100 * (eff - 1))

def test_cash_out_overrides_outcome():
    pl = bm.settle_profit(stake=100, decimal_odds=2.5, outcome="loss", cash_out_amount=120)
    assert pl == pytest.approx(20.0)

def test_each_way_winner():
    # stake 100 total (50 win + 50 place), odds 5.0, place 1/4 -> place odds 2.0
    # win part: 50*4 = 200 ; place part: 50*1 = 50 ; total profit 250
    pl = bm.settle_profit(stake=100, decimal_odds=5.0, outcome="win",
                          each_way=True, place_fraction=0.25)
    assert pl == pytest.approx(250.0)

def test_each_way_placed_only():
    # lost the win part (-50), placed the place part (+50) -> net 0
    pl = bm.settle_profit(stake=100, decimal_odds=5.0, outcome="loss",
                          each_way=True, place_fraction=0.25, placed=True)
    assert pl == pytest.approx(0.0)


def test_each_way_outcome_placed():
    pl = bm.settle_profit(stake=100, decimal_odds=5.0, outcome="placed",
                          each_way=True, place_fraction=0.25)
    assert pl == pytest.approx(0.0)


def test_lay_liability_helper():
    assert bm.lay_liability(10, 3.0) == pytest.approx(20.0)


def test_lay_win_no_commission():
    assert bm.settle_profit(stake=10, decimal_odds=3.0, outcome="win", side="lay") == pytest.approx(10.0)


def test_lay_win_with_commission():
    pl = bm.settle_profit(stake=10, decimal_odds=3.0, outcome="win",
                          exchange_commission_pct=5, side="lay")
    assert pl == pytest.approx(9.5)


def test_lay_loss():
    pl = bm.settle_profit(stake=10, decimal_odds=3.0, outcome="loss", side="lay")
    assert pl == pytest.approx(-20.0)


def test_portfolio_metrics_lay_uses_liability_turnover():
    rows = [
        {"stake": 10, "profit": 10, "outcome": "win", "side": "lay", "decimal_odds": 3.0},
        {"stake": 10, "profit": -20, "outcome": "loss", "side": "lay", "decimal_odds": 3.0},
    ]
    m = bm.portfolio_metrics(rows)
    assert m["turnover"] == pytest.approx(40.0)  # 20 liability each
    assert m["profit"] == pytest.approx(-10.0)


# ------------------------------- metrics --------------------------------- #

def test_portfolio_metrics():
    rows = [
        {"stake": 100, "profit": 150, "outcome": "win"},
        {"stake": 100, "profit": -100, "outcome": "loss"},
        {"stake": 100, "profit": -100, "outcome": "loss"},
        {"stake": 100, "profit": 0, "outcome": "void"},
        {"stake": 100, "profit": 0, "outcome": "pending"},  # excluded
    ]
    m = bm.portfolio_metrics(rows)
    assert m["settled_bets"] == 4
    assert m["profit"] == pytest.approx(-50.0)
    assert m["turnover"] == pytest.approx(400.0)
    assert m["yield_pct"] == pytest.approx(-12.5)
    assert m["wins"] == 1
    assert m["strike_rate_pct"] == pytest.approx(25.0)


def test_portfolio_metrics_pending_cash_out():
    rows = [
        {"stake": 100, "profit": 10, "outcome": "pending", "cash_out_amount": 110},
        {"stake": 100, "profit": 20, "outcome": "loss", "cash_out_amount": 120},
    ]
    m = bm.portfolio_metrics(rows)
    assert m["settled_bets"] == 2
    assert m["profit"] == pytest.approx(30.0)
    assert m["wins"] == 2


def test_clv():
    # took 2.50, closed 2.30 -> beat the close
    assert bm.closing_line_value(2.5, 2.3) == pytest.approx(8.7, abs=0.1)


def test_current_bankroll():
    assert current_bankroll(1000, 150) == 1150.0
    assert current_bankroll(1000, -100) == 900.0
    assert current_bankroll(0, 50) == 50.0

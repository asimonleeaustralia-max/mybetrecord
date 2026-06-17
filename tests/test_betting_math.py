"""Tests for the betting math — the part that must never be wrong."""

import math

import pytest

from betrecord_shared import betting_math as bm


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


def test_clv():
    # took 2.50, closed 2.30 -> beat the close
    assert bm.closing_line_value(2.5, 2.3) == pytest.approx(8.7, abs=0.1)

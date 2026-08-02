package com.mybetrecord.android

import com.mybetrecord.android.util.BetMath
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * BetMath.settleProfit is a port of settle_profit in
 * shared/betrecord_shared/betting_math.py, used to show a plausible P/L for
 * bets recorded offline. These cases pin it to the backend's behaviour so the
 * two cannot drift apart unnoticed.
 */
class SettleProfitTest {

    private fun profit(
        stake: Double,
        odds: Double,
        outcome: String,
        eachWay: Boolean = false,
        placeFraction: Double = 0.25,
        placed: Boolean = false,
        commission: Double = 0.0,
        cashOut: Double? = null,
        side: String = "back",
        freeBet: Boolean = false,
    ) = BetMath.settleProfit(
        stake = stake,
        decimalOdds = odds,
        outcome = outcome,
        eachWay = eachWay,
        placeFraction = placeFraction,
        placed = placed,
        exchangeCommissionPct = commission,
        cashOutAmount = cashOut,
        side = side,
        freeBet = freeBet,
    )

    @Test
    fun pendingAndVoidRecordNothing() {
        assertEquals(0.0, profit(50.0, 2.5, "pending"), 1e-9)
        assertEquals(0.0, profit(50.0, 2.5, "void"), 1e-9)
        // An unknown outcome must not invent a number.
        assertEquals(0.0, profit(50.0, 2.5, "something_else"), 1e-9)
    }

    @Test
    fun straightBackWinAndLoss() {
        assertEquals(75.0, profit(50.0, 2.5, "win"), 1e-9)
        assertEquals(-50.0, profit(50.0, 2.5, "loss"), 1e-9)
    }

    @Test
    fun asianHandicapHalves() {
        assertEquals(37.5, profit(50.0, 2.5, "half_win"), 1e-9)
        assertEquals(-25.0, profit(50.0, 2.5, "half_loss"), 1e-9)
    }

    @Test
    fun freeBetDoesNotReturnStakeAndLossesAreZero() {
        // Winnings only — the promotion stake is not returned.
        assertEquals(75.0, profit(50.0, 2.5, "win", freeBet = true), 1e-9)
        // No own money at risk, so a loss records nothing.
        assertEquals(0.0, profit(50.0, 2.5, "loss", freeBet = true), 1e-9)
        assertEquals(0.0, profit(50.0, 2.5, "half_loss", freeBet = true), 1e-9)
    }

    @Test
    fun layWinsBackersStakeAndLosesLiability() {
        assertEquals(10.0, profit(10.0, 3.0, "win", side = "lay"), 1e-9)
        assertEquals(-20.0, profit(10.0, 3.0, "loss", side = "lay"), 1e-9)
    }

    @Test
    fun eachWaySplitsStakeAcrossWinAndPlaceParts() {
        // £20 total = £10 win + £10 place at 1/4 odds of 5.0 → place odds 2.0.
        // Win: 10*(5-1)=40, place: 10*(2-1)=10 → 50.
        assertEquals(50.0, profit(20.0, 5.0, "win", eachWay = true), 1e-9)
        // Placed only: win part loses the unit, place part returns 10 → 0.
        assertEquals(0.0, profit(20.0, 5.0, "placed", eachWay = true), 1e-9)
        // Both parts lose.
        assertEquals(-20.0, profit(20.0, 5.0, "loss", eachWay = true), 1e-9)
    }

    @Test
    fun eachWayPlacedFlagCountsEvenWhenOutcomeIsLoss() {
        // The backend normalises this to a "placed" outcome; the maths agrees.
        assertEquals(0.0, profit(20.0, 5.0, "loss", eachWay = true, placed = true), 1e-9)
    }

    @Test
    fun commissionAppliesToWinningsOnly() {
        // 5% of the 75 net win.
        assertEquals(71.25, profit(50.0, 2.5, "win", commission = 5.0), 1e-9)
        // Losses are untouched by a winnings deduction.
        assertEquals(-50.0, profit(50.0, 2.5, "loss", commission = 5.0), 1e-9)
    }

    @Test
    fun cashOutOverridesOutcome() {
        assertEquals(10.0, profit(50.0, 2.5, "loss", cashOut = 60.0), 1e-9)
        assertEquals(-20.0, profit(50.0, 2.5, "win", cashOut = 30.0), 1e-9)
        // A free-bet cash-out keeps the whole amount; there was no stake to return.
        assertEquals(60.0, profit(50.0, 2.5, "win", cashOut = 60.0, freeBet = true), 1e-9)
    }

    @Test
    fun resultsRoundToTwoDecimals() {
        // 33.33 * (1.333 - 1) = 11.098... → 11.1
        assertEquals(11.1, profit(33.33, 1.333, "win"), 1e-9)
    }
}

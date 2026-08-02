package com.mybetrecord.android.util

/**
 * Client-side betting maths, ported from the web app (frontend/src/app.js) so the
 * two clients agree. The backend remains the source of truth for stored values.
 */
object BetMath {

    /** Parses "11/8" (or "11") into numerator/denominator. Returns null when invalid. */
    fun parseFractional(text: String): Pair<Double, Double>? {
        val parts = text.trim().split('/')
        val num = parts.getOrNull(0)?.trim()?.toDoubleOrNull() ?: return null
        val den = when (parts.size) {
            1 -> 1.0
            2 -> parts[1].trim().toDoubleOrNull() ?: return null
            else -> return null
        }
        if (num <= 0 || den <= 0) return null
        return num to den
    }

    fun fractionalToDecimal(numerator: Double, denominator: Double): Double =
        1 + numerator / denominator

    /** Liability on a lay bet: what you pay out if the selection wins. */
    fun layLiability(backersStake: Double, oddsDecimal: Double): Double? {
        if (backersStake <= 0 || oddsDecimal <= 1) return null
        return Math.round(backersStake * (oddsDecimal - 1) * 100) / 100.0
    }

    /** Edge per unit staked, in percent, from bookmaker odds vs your implied (fair) odds. */
    fun edgePct(oddsDecimal: Double, impliedDecimal: Double): Double? {
        if (oddsDecimal <= 1 || impliedDecimal <= 1) return null
        val p = 1 / impliedDecimal
        return (p * (oddsDecimal - 1) - (1 - p)) * 100
    }

    data class KellyResult(val fraction: Double, val stake: Double)

    /** Kelly fraction and stake; fraction is already scaled by the multiplier. */
    fun kelly(
        oddsDecimal: Double,
        impliedDecimal: Double,
        bankroll: Double,
        multiplier: Double = 1.0,
    ): KellyResult? {
        if (oddsDecimal <= 1 || impliedDecimal <= 1 || bankroll <= 0) return null
        val b = oddsDecimal - 1
        val p = 1 / impliedDecimal
        val q = 1 - p
        val f = maxOf(0.0, (b * p - q) / b) * (if (multiplier > 0) multiplier else 1.0)
        return KellyResult(fraction = f, stake = f * bankroll)
    }

    /** Combined decimal odds of a multiple: the product of its legs. */
    fun combinedOdds(legOdds: List<Double>): Double? {
        if (legOdds.size < 2 || legOdds.any { it <= 1 }) return null
        return legOdds.fold(1.0) { acc, o -> acc * o }
    }

    /**
     * Profit/loss for one bet, ported from settle_profit in
     * shared/betrecord_shared/betting_math.py.
     *
     * Used only to fill in a plausible P/L for a bet recorded offline, so the
     * ledger and reports read sensibly before the server settles it for real.
     * The server's value overwrites this as soon as the change syncs.
     */
    fun settleProfit(
        stake: Double,
        decimalOdds: Double,
        outcome: String,
        eachWay: Boolean = false,
        placeFraction: Double = 0.25,
        placed: Boolean = false,
        exchangeCommissionPct: Double = 0.0,
        cashOutAmount: Double? = null,
        side: String = "back",
        freeBet: Boolean = false,
    ): Double {
        fun round2(v: Double) = Math.round(v * 100) / 100.0

        // A cash-out overrides the outcome entirely.
        if (cashOutAmount != null) {
            return round2(if (freeBet) cashOutAmount else cashOutAmount - stake)
        }

        val result = outcome.lowercase().ifBlank { "pending" }
        if (result == "pending" || result == "void") return 0.0

        val isLay = side.lowercase() == "lay"
        val gross = when {
            isLay -> when {
                eachWay -> 0.0
                result == "win" -> stake
                result == "loss" -> -(layLiability(stake, decimalOdds) ?: 0.0)
                else -> 0.0
            }
            !eachWay -> when (result) {
                "win" -> stake * (decimalOdds - 1.0)
                "half_win" -> 0.5 * stake * (decimalOdds - 1.0)
                "half_loss" -> if (freeBet) 0.0 else -0.5 * stake
                "loss" -> if (freeBet) 0.0 else -stake
                else -> 0.0
            }
            else -> {
                // Each way: the stake covers both parts, so a unit is half of it.
                val unit = stake / 2.0
                val winPart = if (result == "win") {
                    unit * (decimalOdds - 1.0)
                } else {
                    if (freeBet) 0.0 else -unit
                }
                val placeOdds = 1.0 + (decimalOdds - 1.0) * placeFraction
                val placePart = if (placed || result == "win" || result == "placed") {
                    unit * (placeOdds - 1.0)
                } else {
                    if (freeBet) 0.0 else -unit
                }
                winPart + placePart
            }
        }

        // Deductions apply to net winnings only.
        val commission = if (gross > 0 && exchangeCommissionPct != 0.0) {
            gross * (exchangeCommissionPct / 100.0)
        } else {
            0.0
        }
        return round2(gross - commission)
    }
}

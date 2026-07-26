package com.mybetrecord.android

import com.mybetrecord.android.util.BetMath
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BetMathTest {

    @Test
    fun parseFractional_parsesNumeratorAndDenominator() {
        assertEquals(11.0 to 8.0, BetMath.parseFractional("11/8"))
        assertEquals(6.0 to 1.0, BetMath.parseFractional("6"))
        assertNull(BetMath.parseFractional("abc"))
        assertNull(BetMath.parseFractional("11/0"))
        assertNull(BetMath.parseFractional("1/2/3"))
    }

    @Test
    fun fractionalToDecimal_matchesBackend() {
        assertEquals(2.375, BetMath.fractionalToDecimal(11.0, 8.0), 1e-9)
        assertEquals(2.5, BetMath.fractionalToDecimal(6.0, 4.0), 1e-9)
    }

    @Test
    fun layLiability_matchesWebFormula() {
        // stake * (odds - 1), rounded to 2 dp — same as computeLayLiability in app.js.
        assertEquals(15.0, BetMath.layLiability(10.0, 2.5)!!, 1e-9)
        assertNull(BetMath.layLiability(0.0, 2.5))
        assertNull(BetMath.layLiability(10.0, 1.0))
    }

    @Test
    fun edgePct_matchesWebFormula() {
        // odds 2.5, implied 2.0 → p=0.5 → (0.5*1.5 - 0.5)*100 = 25%.
        assertEquals(25.0, BetMath.edgePct(2.5, 2.0)!!, 1e-9)
        assertNull(BetMath.edgePct(1.0, 2.0))
    }

    @Test
    fun kelly_matchesWebFormula() {
        // b=1.5, p=0.5, q=0.5 → f = (0.75-0.5)/1.5 = 1/6.
        val result = BetMath.kelly(2.5, 2.0, 600.0, 1.0)!!
        assertEquals(1.0 / 6.0, result.fraction, 1e-9)
        assertEquals(100.0, result.stake, 1e-9)

        // Half-Kelly multiplier halves both.
        val half = BetMath.kelly(2.5, 2.0, 600.0, 0.5)!!
        assertEquals(50.0, half.stake, 1e-9)

        // No edge → zero stake, never negative.
        val noEdge = BetMath.kelly(1.8, 2.0, 600.0, 1.0)!!
        assertEquals(0.0, noEdge.fraction, 1e-9)
    }

    @Test
    fun combinedOdds_isProductOfLegs() {
        assertEquals(6.0, BetMath.combinedOdds(listOf(2.0, 3.0))!!, 1e-9)
        assertNull(BetMath.combinedOdds(listOf(2.0)))
        assertNull(BetMath.combinedOdds(listOf(2.0, 1.0)))
    }
}

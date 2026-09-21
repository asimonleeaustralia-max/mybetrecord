import XCTest
@testable import MyBetRecord

final class BetMathTests: XCTestCase {
    func testParseFractional() {
        XCTAssertEqual(BetMath.parseFractional("11/8")?.numerator, 11)
        XCTAssertEqual(BetMath.parseFractional("11/8")?.denominator, 8)
        XCTAssertEqual(BetMath.parseFractional("6")?.numerator, 6)
        XCTAssertNil(BetMath.parseFractional("abc"))
        XCTAssertNil(BetMath.parseFractional("11/0"))
    }

    func testFractionalToDecimal() {
        XCTAssertEqual(BetMath.fractionalToDecimal(numerator: 11, denominator: 8), 2.375, accuracy: 1e-9)
    }

    func testAmericanToDecimal() {
        XCTAssertEqual(BetMath.toDecimal("+150", format: "american")!, 2.5, accuracy: 1e-9)
        XCTAssertEqual(BetMath.toDecimal("-200", format: "american")!, 1.5, accuracy: 1e-9)
    }

    func testHongKongAndAsian() {
        XCTAssertEqual(BetMath.toDecimal("0.85", format: "hong_kong")!, 1.85, accuracy: 1e-9)
        XCTAssertEqual(BetMath.toDecimal("+0.85", format: "malaysian")!, 1.85, accuracy: 1e-9)
        XCTAssertEqual(BetMath.toDecimal("-0.85", format: "malaysian")!, 1 + 1 / 0.85, accuracy: 1e-9)
    }

    func testOddsForApiAmericanNegative() {
        let pair = BetMath.oddsForApi("-200", format: "american")
        XCTAssertEqual(pair?.odds, -200, accuracy: 1e-9)
        XCTAssertNil(pair?.denominator)
    }

    func testFormatFromDecimalRoundTrip() {
        let american = BetMath.formatFromDecimal(2.5, format: "american")
        XCTAssertEqual(american, "+150")
        let fractional = BetMath.formatFromDecimal(2.375, format: "fractional")
        XCTAssertEqual(fractional, "11/8")
    }

    func testLayLiability() {
        XCTAssertEqual(BetMath.layLiability(backersStake: 10, oddsDecimal: 2.5)!, 15, accuracy: 1e-9)
        XCTAssertNil(BetMath.layLiability(backersStake: 0, oddsDecimal: 2.5))
    }

    func testEdgePct() {
        XCTAssertEqual(BetMath.edgePct(oddsDecimal: 2.5, impliedDecimal: 2.0)!, 25, accuracy: 1e-9)
    }

    func testKelly() {
        let result = BetMath.kelly(oddsDecimal: 2.5, impliedDecimal: 2.0, bankroll: 600, multiplier: 1)!
        XCTAssertEqual(result.fraction, 1.0 / 6.0, accuracy: 1e-9)
        XCTAssertEqual(result.stake, 100, accuracy: 1e-9)
    }

    func testCombinedOdds() {
        XCTAssertEqual(BetMath.combinedOdds([2, 3])!, 6, accuracy: 1e-9)
        XCTAssertNil(BetMath.combinedOdds([2]))
    }

    func testSettleProfitBackWin() {
        let profit = BetMath.settleProfit(stake: 10, oddsDecimal: 2.5, outcome: "win")
        XCTAssertEqual(profit!, 15, accuracy: 1e-9)
    }

    func testSettleProfitFreeBetLoss() {
        let profit = BetMath.settleProfit(stake: 10, oddsDecimal: 2.5, outcome: "loss", freeBet: true)
        XCTAssertEqual(profit!, 0, accuracy: 1e-9)
    }

    func testSettleProfitCashOut() {
        let profit = BetMath.settleProfit(stake: 10, oddsDecimal: 2.5, outcome: "pending", cashOutAmount: 12)
        XCTAssertEqual(profit!, 2, accuracy: 1e-9)
    }

    func testSettleProfitLay() {
        let win = BetMath.settleProfit(stake: 10, oddsDecimal: 2.5, outcome: "win", side: "lay")
        XCTAssertEqual(win!, 10, accuracy: 1e-9)
        let loss = BetMath.settleProfit(stake: 10, oddsDecimal: 2.5, outcome: "loss", side: "lay")
        XCTAssertEqual(loss!, -15, accuracy: 1e-9)
    }

    func testSettleProfitEachWayPlaced() {
        let profit = BetMath.settleProfit(
            stake: 20,
            oddsDecimal: 5,
            outcome: "placed",
            eachWay: true,
            placeFraction: 0.25
        )
        // unit 10; place odds 2.0; place profit 10; win part -10 → 0
        XCTAssertEqual(profit!, 0, accuracy: 1e-9)
    }

    func testEffectiveOdds() {
        let eff = BetMath.effectiveDecimalOdds(oddsDecimal: 2.0, commissionPct: 5)
        XCTAssertEqual(eff!, 1.95, accuracy: 1e-9)
    }
}

@MainActor
final class AuthRepositoryRefreshTests: XCTestCase {
    func testPersistTokensSetsLoggedIn() {
        let store = TokenStore()
        let api = APIClient(tokenStore: store)
        let repo = AuthRepository(api: api, tokenStore: store)
        XCTAssertFalse(repo.isLoggedIn)
        repo.persistTokens(TokenResponse(accessToken: "a", tokenType: "bearer", expiresIn: 60, refreshToken: "r", refreshExpiresIn: 3600))
        XCTAssertTrue(repo.isLoggedIn)
        XCTAssertEqual(store.getAccessToken(), "a")
        XCTAssertEqual(store.getRefreshToken(), "r")
    }

    func testClearSession() {
        let store = TokenStore()
        let repo = AuthRepository(api: APIClient(tokenStore: store), tokenStore: store)
        repo.persistTokens(TokenResponse(accessToken: "a", tokenType: "bearer", expiresIn: 60, refreshToken: "r", refreshExpiresIn: 3600))
        repo.clearSession()
        XCTAssertFalse(repo.isLoggedIn)
        XCTAssertNil(store.getRefreshToken())
    }
}

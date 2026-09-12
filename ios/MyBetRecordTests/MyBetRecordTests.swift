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

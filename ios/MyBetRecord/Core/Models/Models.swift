import Foundation

// MARK: - Auth

struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String
    let expiresIn: Int
    let refreshToken: String?
    let refreshExpiresIn: Int?
}

struct LoginRequest: Codable {
    let email: String
    let password: String
    let client: String
    let deviceName: String?
}

struct RegisterRequest: Codable {
    let email: String
    let password: String
    let timezone: String?
}

struct RegisterResponse: Codable {
    let message: String
    let verificationToken: String?
}

struct RefreshRequest: Codable {
    let refreshToken: String
}

struct LogoutRequest: Codable {
    let refreshToken: String?
    let allDevices: Bool
}

struct PasswordResetRequest: Codable {
    let email: String
}

struct PasswordResetConfirm: Codable {
    let token: String
    let password: String
}

struct AccountDeleteRequest: Codable {
    let password: String
    let confirm: String
}

struct User: Codable, Equatable {
    let id: String
    let email: String
    var defaultOddsFormat: String
    var baseCurrency: String
    var bankroll: Double
    var kellyMultiplier: Double
    var preferredLocale: String
    var timezone: String
    let isAdmin: Bool
    let createdAt: String?
    var plan: String
    let planCurrency: String?
    let subscriptionStatus: String?
    let subscriptionCancelAtPeriodEnd: Bool
    let subscriptionCurrentPeriodEnd: String?
    let compProUntil: String?
    let isPro: Bool
    var publicBetsEnabled: Bool
    let publicBetsToken: String?
    var accountDescription: String?
    var displayName: String?
}

struct SettingsUpdate: Codable {
    var defaultOddsFormat: String?
    var baseCurrency: String?
    var bankroll: Double?
    var kellyMultiplier: Double?
    var preferredLocale: String?
    var timezone: String?
    var publicBetsEnabled: Bool?
    var accountDescription: String?
    var displayName: String?
}

// MARK: - Bets

struct BetLeg: Codable, Equatable {
    let legIndex: Int
    let event: String
    let selection: String
    let oddsDecimal: Double
    let oddsFormat: String
}

struct Bet: Codable, Equatable, Identifiable {
    let id: String
    var tournament: String?
    var event: String
    var selection: String
    var sport: String
    var betType: String
    var side: String
    var isMultiple: Bool
    var legs: [BetLeg]
    var placedAt: String
    var eventAt: String?
    var settledAt: String?
    var oddsDecimal: Double
    var oddsFormat: String
    var stake: Double
    var currency: String
    var eachWay: Bool
    var placeFraction: Double
    var placed: Bool
    var freeBet: Bool
    var outcome: String
    var profit: Double
    var cashOutAmount: Double?
    var betModel: String?
    var modelImpliedOdds: Double?
    var personalImpliedOdds: Double?
    var tipsterImpliedOdds: Double?
    var personalEdgePct: Double?
    var modelEdgePct: Double?
    var tipsterEdgePct: Double?
    var kellyStake: Double?
    var modelKellyStake: Double?
    var bookmaker: String?
    var portal: String?
    var exchangeCommissionPct: Double?
    var tipster: String?
    var betBroker: String?
    var notes: String?
    var closingOdds: Double?
    var closingOddsExchange: Double?
    var clvPct: Double?
    var edgePct: Double?
    var shareToken: String?
    var createdAt: String?
    var updatedAt: String?
}

struct BetLegCreate: Codable {
    let event: String
    let selection: String
    let odds: Double
    let oddsFormat: String?
    let oddsDenominator: Double?
}

struct BetCreate: Codable {
    let sport: String
    let event: String?
    let selection: String?
    let odds: Double?
    let stake: Double
    let betType: String
    let side: String
    let currency: String
    let oddsFormat: String
    let oddsDenominator: Double?
    let outcome: String
    let tournament: String?
    let bookmaker: String?
    let portal: String?
    let exchangeCommissionPct: Double?
    let tipster: String?
    let betBroker: String?
    let notes: String?
    let eachWay: Bool
    let placeFraction: Double?
    let placed: Bool
    let freeBet: Bool
    let isMultiple: Bool
    let legs: [BetLegCreate]?
    let cashOutAmount: Double?
    let betModel: String?
    let modelImpliedOdds: Double?
    let personalImpliedOdds: Double?
    let tipsterImpliedOdds: Double?
    let closingOdds: Double?
    let closingOddsExchange: Double?
    let placedAt: String?
    let eventAt: String?
    let settledAt: String?
}

struct BetUpdate: Codable {
    var sport: String?
    var event: String?
    var selection: String?
    var odds: Double?
    var stake: Double?
    var betType: String?
    var side: String?
    var currency: String?
    var oddsFormat: String?
    var oddsDenominator: Double?
    var outcome: String?
    var tournament: String?
    var bookmaker: String?
    var portal: String?
    var exchangeCommissionPct: Double?
    var tipster: String?
    var betBroker: String?
    var notes: String?
    var eachWay: Bool?
    var placeFraction: Double?
    var placed: Bool?
    var freeBet: Bool?
    var isMultiple: Bool?
    var legs: [BetLegCreate]?
    var cashOutAmount: Double?
    var betModel: String?
    var modelImpliedOdds: Double?
    var personalImpliedOdds: Double?
    var tipsterImpliedOdds: Double?
    var closingOdds: Double?
    var closingOddsExchange: Double?
    var eventAt: String?
    var placedAt: String?
    var settledAt: String?
}

struct BetShare: Codable {
    let shareToken: String
}

// MARK: - Reports

struct EquityPoint: Codable, Identifiable {
    var id: String { date }
    let date: String
    let profit: Double
    let cumulative: Double
}

struct ReportSummary: Codable {
    let turnover: Double
    let profit: Double
    let yieldPct: Double
    let roiPct: Double
    let strikeRatePct: Double
    let settledBets: Int
    let wins: Int
    let losses: Int
    let voids: Int
    let bankroll: Double?
    let roiVsBankrollPct: Double?
    let baseCurrency: String?
    let currency: String?
    let totalBets: Int
}

struct MonthlyProfit: Identifiable {
    let id: String
    let month: String
    let profit: Double
}

extension Bet {
    init(
        id: String,
        event: String,
        selection: String,
        sport: String,
        betType: String = "Win",
        oddsDecimal: Double,
        stake: Double,
        currency: String = "GBP",
        outcome: String = "pending",
        profit: Double = 0,
        placedAt: String,
        bookmaker: String? = nil
    ) {
        self.id = id
        self.tournament = nil
        self.event = event
        self.selection = selection
        self.sport = sport
        self.betType = betType
        self.side = "back"
        self.isMultiple = false
        self.legs = []
        self.placedAt = placedAt
        self.eventAt = nil
        self.settledAt = nil
        self.oddsDecimal = oddsDecimal
        self.oddsFormat = "decimal"
        self.stake = stake
        self.currency = currency
        self.eachWay = false
        self.placeFraction = 0.25
        self.placed = false
        self.freeBet = false
        self.outcome = outcome
        self.profit = profit
        self.cashOutAmount = nil
        self.bookmaker = bookmaker
        self.portal = nil
        self.tipster = nil
        self.notes = nil
        self.closingOdds = nil
        self.closingOddsExchange = nil
        self.clvPct = nil
        self.edgePct = nil
        self.shareToken = nil
        self.createdAt = nil
        self.updatedAt = nil
    }
}

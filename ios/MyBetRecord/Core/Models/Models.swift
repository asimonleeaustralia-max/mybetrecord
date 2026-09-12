import Foundation

// MARK: - Auth

struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String
    let expiresIn: Int
    let refreshToken: String?
    let refreshExpiresIn: Int?

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
        case refreshToken = "refresh_token"
        case refreshExpiresIn = "refresh_expires_in"
    }
}

struct LoginRequest: Codable {
    let email: String
    let password: String
    let client: String
    let deviceName: String?

    enum CodingKeys: String, CodingKey {
        case email, password, client
        case deviceName = "device_name"
    }
}

struct RegisterRequest: Codable {
    let email: String
    let password: String
    let timezone: String?
}

struct RegisterResponse: Codable {
    let message: String
    let verificationToken: String?

    enum CodingKeys: String, CodingKey {
        case message
        case verificationToken = "verification_token"
    }
}

struct RefreshRequest: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

struct LogoutRequest: Codable {
    let refreshToken: String?
    let allDevices: Bool

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
        case allDevices = "all_devices"
    }
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

    enum CodingKeys: String, CodingKey {
        case id, email, bankroll, timezone, plan
        case defaultOddsFormat = "default_odds_format"
        case baseCurrency = "base_currency"
        case kellyMultiplier = "kelly_multiplier"
        case preferredLocale = "preferred_locale"
        case isAdmin = "is_admin"
        case createdAt = "created_at"
        case planCurrency = "plan_currency"
        case subscriptionStatus = "subscription_status"
        case subscriptionCancelAtPeriodEnd = "subscription_cancel_at_period_end"
        case subscriptionCurrentPeriodEnd = "subscription_current_period_end"
        case compProUntil = "comp_pro_until"
        case isPro = "is_pro"
        case publicBetsEnabled = "public_bets_enabled"
        case publicBetsToken = "public_bets_token"
        case accountDescription = "account_description"
        case displayName = "display_name"
    }
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

    enum CodingKeys: String, CodingKey {
        case bankroll, timezone
        case defaultOddsFormat = "default_odds_format"
        case baseCurrency = "base_currency"
        case kellyMultiplier = "kelly_multiplier"
        case preferredLocale = "preferred_locale"
        case publicBetsEnabled = "public_bets_enabled"
        case accountDescription = "account_description"
        case displayName = "display_name"
    }
}

// MARK: - Bets

struct BetLeg: Codable, Equatable {
    let legIndex: Int
    let event: String
    let selection: String
    let oddsDecimal: Double
    let oddsFormat: String

    enum CodingKeys: String, CodingKey {
        case event, selection
        case legIndex = "leg_index"
        case oddsDecimal = "odds_decimal"
        case oddsFormat = "odds_format"
    }
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
    var bookmaker: String?
    var portal: String?
    var tipster: String?
    var notes: String?
    var closingOdds: Double?
    var closingOddsExchange: Double?
    var clvPct: Double?
    var edgePct: Double?
    var shareToken: String?
    var createdAt: String?
    var updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, tournament, event, selection, sport, side, legs, stake, currency, outcome, profit, bookmaker, portal, tipster, notes, placed
        case betType = "bet_type"
        case isMultiple = "is_multiple"
        case placedAt = "placed_at"
        case eventAt = "event_at"
        case settledAt = "settled_at"
        case oddsDecimal = "odds_decimal"
        case oddsFormat = "odds_format"
        case eachWay = "each_way"
        case placeFraction = "place_fraction"
        case freeBet = "free_bet"
        case cashOutAmount = "cash_out_amount"
        case closingOdds = "closing_odds"
        case closingOddsExchange = "closing_odds_exchange"
        case clvPct = "clv_pct"
        case edgePct = "edge_pct"
        case shareToken = "share_token"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct BetLegCreate: Codable {
    let event: String
    let selection: String
    let odds: Double
    let oddsFormat: String?
    let oddsDenominator: Double?

    enum CodingKeys: String, CodingKey {
        case event, selection, odds
        case oddsFormat = "odds_format"
        case oddsDenominator = "odds_denominator"
    }
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
    let tipster: String?
    let notes: String?
    let eachWay: Bool
    let placed: Bool
    let freeBet: Bool
    let isMultiple: Bool
    let legs: [BetLegCreate]?
    let cashOutAmount: Double?
    let closingOdds: Double?
    let placedAt: String?
    let eventAt: String?

    enum CodingKeys: String, CodingKey {
        case sport, event, selection, odds, stake, side, currency, outcome, tournament, bookmaker, portal, tipster, notes, placed, legs
        case betType = "bet_type"
        case oddsFormat = "odds_format"
        case oddsDenominator = "odds_denominator"
        case eachWay = "each_way"
        case freeBet = "free_bet"
        case isMultiple = "is_multiple"
        case cashOutAmount = "cash_out_amount"
        case closingOdds = "closing_odds"
        case placedAt = "placed_at"
        case eventAt = "event_at"
    }
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
    var tipster: String?
    var notes: String?
    var eachWay: Bool?
    var placed: Bool?
    var freeBet: Bool?
    var isMultiple: Bool?
    var legs: [BetLegCreate]?
    var cashOutAmount: Double?
    var closingOdds: Double?
    var eventAt: String?

    enum CodingKeys: String, CodingKey {
        case sport, event, selection, odds, stake, side, currency, outcome, tournament, bookmaker, portal, tipster, notes, placed, legs
        case betType = "bet_type"
        case oddsFormat = "odds_format"
        case oddsDenominator = "odds_denominator"
        case eachWay = "each_way"
        case freeBet = "free_bet"
        case isMultiple = "is_multiple"
        case cashOutAmount = "cash_out_amount"
        case closingOdds = "closing_odds"
        case eventAt = "event_at"
    }
}

struct BetShare: Codable {
    let shareToken: String

    enum CodingKeys: String, CodingKey {
        case shareToken = "share_token"
    }
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

    enum CodingKeys: String, CodingKey {
        case turnover, profit, bankroll, currency, wins, losses, voids
        case yieldPct = "yield_pct"
        case roiPct = "roi_pct"
        case strikeRatePct = "strike_rate_pct"
        case settledBets = "settled_bets"
        case roiVsBankrollPct = "roi_vs_bankroll_pct"
        case baseCurrency = "base_currency"
        case totalBets = "total_bets"
    }
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

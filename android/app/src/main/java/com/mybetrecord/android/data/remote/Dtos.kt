package com.mybetrecord.android.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class TokenResponseDto(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Int,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("refresh_expires_in") val refreshExpiresIn: Int? = null,
)

@Serializable
data class LoginRequestDto(
    val email: String,
    val password: String,
    val client: String = "android",
    @SerialName("device_name") val deviceName: String? = "Android",
)

@Serializable
data class RegisterRequestDto(
    val email: String,
    val password: String,
    val timezone: String? = null,
)

@Serializable
data class RegisterResponseDto(
    val message: String,
    @SerialName("verification_token") val verificationToken: String? = null,
)

@Serializable
data class RefreshRequestDto(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequestDto(
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("all_devices") val allDevices: Boolean = false,
)

@Serializable
data class PasswordResetRequestDto(
    val email: String,
)

@Serializable
data class PasswordResetConfirmDto(
    val token: String,
    val password: String,
)

@Serializable
data class AccountDeleteRequestDto(
    val password: String,
    val confirm: String = "DELETE",
)

@Serializable
data class UserDto(
    val id: String,
    val email: String,
    @SerialName("default_odds_format") val defaultOddsFormat: String = "decimal",
    @SerialName("base_currency") val baseCurrency: String = "GBP",
    val bankroll: Double = 0.0,
    @SerialName("kelly_multiplier") val kellyMultiplier: Double = 1.0,
    @SerialName("preferred_locale") val preferredLocale: String = "en",
    val timezone: String = "UTC",
    @SerialName("is_admin") val isAdmin: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
    val plan: String = "free",
    @SerialName("plan_currency") val planCurrency: String? = null,
    @SerialName("subscription_status") val subscriptionStatus: String? = null,
    @SerialName("subscription_cancel_at_period_end") val subscriptionCancelAtPeriodEnd: Boolean = false,
    @SerialName("subscription_current_period_end") val subscriptionCurrentPeriodEnd: String? = null,
    @SerialName("comp_pro_until") val compProUntil: String? = null,
    @SerialName("is_pro") val isPro: Boolean = false,
    @SerialName("public_bets_enabled") val publicBetsEnabled: Boolean = false,
    @SerialName("public_bets_token") val publicBetsToken: String? = null,
    @SerialName("account_description") val accountDescription: String? = null,
    @SerialName("display_name") val displayName: String? = null,
)

@Serializable
data class SettingsUpdateDto(
    @SerialName("default_odds_format") val defaultOddsFormat: String? = null,
    @SerialName("base_currency") val baseCurrency: String? = null,
    val bankroll: Double? = null,
    @SerialName("kelly_multiplier") val kellyMultiplier: Double? = null,
    @SerialName("preferred_locale") val preferredLocale: String? = null,
    val timezone: String? = null,
    @SerialName("public_bets_enabled") val publicBetsEnabled: Boolean? = null,
    @SerialName("account_description") val accountDescription: String? = null,
    @SerialName("display_name") val displayName: String? = null,
)

@Serializable
data class BetDto(
    val id: String,
    val tournament: String? = null,
    val event: String,
    val selection: String,
    val sport: String,
    @SerialName("bet_type") val betType: String = "Win",
    val side: String = "back",
    @SerialName("is_multiple") val isMultiple: Boolean = false,
    val legs: List<BetLegDto> = emptyList(),
    @SerialName("placed_at") val placedAt: String,
    @SerialName("event_at") val eventAt: String? = null,
    @SerialName("settled_at") val settledAt: String? = null,
    @SerialName("odds_decimal") val oddsDecimal: Double,
    @SerialName("odds_format") val oddsFormat: String = "decimal",
    val stake: Double,
    val currency: String = "GBP",
    @SerialName("each_way") val eachWay: Boolean = false,
    @SerialName("place_fraction") val placeFraction: Double = 0.25,
    val placed: Boolean = false,
    @SerialName("free_bet") val freeBet: Boolean = false,
    val outcome: String = "pending",
    val profit: Double = 0.0,
    @SerialName("cash_out_amount") val cashOutAmount: Double? = null,
    val bookmaker: String? = null,
    val portal: String? = null,
    val tipster: String? = null,
    val notes: String? = null,
    @SerialName("closing_odds") val closingOdds: Double? = null,
    @SerialName("closing_odds_exchange") val closingOddsExchange: Double? = null,
    @SerialName("clv_pct") val clvPct: Double? = null,
    @SerialName("edge_pct") val edgePct: Double? = null,
    @SerialName("share_token") val shareToken: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class BetLegDto(
    @SerialName("leg_index") val legIndex: Int = 0,
    val event: String,
    val selection: String,
    @SerialName("odds_decimal") val oddsDecimal: Double = 0.0,
    @SerialName("odds_format") val oddsFormat: String = "decimal",
)

@Serializable
data class BetLegCreateDto(
    val event: String,
    val selection: String,
    // Numerator when odds_format is fractional and odds_denominator is set.
    val odds: Double,
    @SerialName("odds_format") val oddsFormat: String? = null,
    @SerialName("odds_denominator") val oddsDenominator: Double? = null,
)

@Serializable
data class BetCreateDto(
    val sport: String,
    val event: String? = null,
    val selection: String? = null,
    val odds: Double? = null,
    val stake: Double,
    @SerialName("bet_type") val betType: String = "Win",
    val side: String = "back",
    val currency: String = "GBP",
    @SerialName("odds_format") val oddsFormat: String = "decimal",
    @SerialName("odds_denominator") val oddsDenominator: Double? = null,
    val outcome: String = "pending",
    val tournament: String? = null,
    val bookmaker: String? = null,
    val portal: String? = null,
    val tipster: String? = null,
    val notes: String? = null,
    @SerialName("each_way") val eachWay: Boolean = false,
    val placed: Boolean = false,
    @SerialName("free_bet") val freeBet: Boolean = false,
    @SerialName("is_multiple") val isMultiple: Boolean = false,
    val legs: List<BetLegCreateDto>? = null,
    @SerialName("cash_out_amount") val cashOutAmount: Double? = null,
    @SerialName("closing_odds") val closingOdds: Double? = null,
    @SerialName("placed_at") val placedAt: String? = null,
    @SerialName("event_at") val eventAt: String? = null,
)

@Serializable
data class BetUpdateDto(
    val sport: String? = null,
    val event: String? = null,
    val selection: String? = null,
    val odds: Double? = null,
    val stake: Double? = null,
    @SerialName("bet_type") val betType: String? = null,
    val side: String? = null,
    val currency: String? = null,
    @SerialName("odds_format") val oddsFormat: String? = null,
    @SerialName("odds_denominator") val oddsDenominator: Double? = null,
    val outcome: String? = null,
    val tournament: String? = null,
    val bookmaker: String? = null,
    val portal: String? = null,
    val tipster: String? = null,
    val notes: String? = null,
    @SerialName("each_way") val eachWay: Boolean? = null,
    val placed: Boolean? = null,
    @SerialName("free_bet") val freeBet: Boolean? = null,
    @SerialName("is_multiple") val isMultiple: Boolean? = null,
    val legs: List<BetLegCreateDto>? = null,
    @SerialName("cash_out_amount") val cashOutAmount: Double? = null,
    @SerialName("closing_odds") val closingOdds: Double? = null,
    @SerialName("event_at") val eventAt: String? = null,
)

@Serializable
data class BetShareDto(
    @SerialName("share_token") val shareToken: String,
)

@Serializable
data class EquityPointDto(
    val date: String,
    val profit: Double,
    val cumulative: Double,
)

@Serializable
data class ReportSummaryDto(
    val turnover: Double = 0.0,
    val profit: Double = 0.0,
    @SerialName("yield_pct") val yieldPct: Double = 0.0,
    @SerialName("roi_pct") val roiPct: Double = 0.0,
    @SerialName("strike_rate_pct") val strikeRatePct: Double = 0.0,
    @SerialName("settled_bets") val settledBets: Int = 0,
    val wins: Int = 0,
    val losses: Int = 0,
    val voids: Int = 0,
    val bankroll: Double? = null,
    @SerialName("roi_vs_bankroll_pct") val roiVsBankrollPct: Double? = null,
    @SerialName("base_currency") val baseCurrency: String? = null,
    val currency: String? = null,
    @SerialName("total_bets") val totalBets: Int = 0,
)

@Serializable
data class ApiErrorDto(
    val detail: JsonElement? = null,
    val message: String? = null,
)

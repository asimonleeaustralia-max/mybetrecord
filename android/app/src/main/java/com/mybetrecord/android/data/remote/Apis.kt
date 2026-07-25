package com.mybetrecord.android.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface AuthApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequestDto): TokenResponseDto

    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequestDto): RegisterResponseDto

    @POST("auth/refresh")
    suspend fun refresh(@Body body: RefreshRequestDto): TokenResponseDto

    @POST("auth/logout")
    suspend fun logout(@Body body: LogoutRequestDto): Response<Unit>

    @GET("auth/me")
    suspend fun me(): UserDto

    @PATCH("auth/settings")
    suspend fun updateSettings(@Body body: SettingsUpdateDto): UserDto

    @HTTP(method = "DELETE", path = "auth/account", hasBody = true)
    suspend fun deleteAccount(@Body body: AccountDeleteRequestDto): Response<Unit>
}

interface BetsApi {
    @GET("bets")
    suspend fun listBets(
        @Query("limit") limit: Int = 200,
        @Query("offset") offset: Int = 0,
    ): List<BetDto>

    @GET("bets/{id}")
    suspend fun getBet(@Path("id") id: String): BetDto

    @POST("bets")
    suspend fun createBet(@Body body: BetCreateDto): BetDto

    @PATCH("bets/{id}")
    suspend fun updateBet(@Path("id") id: String, @Body body: BetUpdateDto): BetDto

    @DELETE("bets/{id}")
    suspend fun deleteBet(@Path("id") id: String): Response<Unit>
}

interface ReportsApi {
    @GET("reports/summary")
    suspend fun summary(
        @Query("use_primary_currency") usePrimaryCurrency: Boolean = true,
    ): ReportSummaryDto
}

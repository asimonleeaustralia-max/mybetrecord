package com.mybetrecord.android.data.repository

import com.mybetrecord.android.data.local.TokenStore
import com.mybetrecord.android.data.remote.AuthApi
import com.mybetrecord.android.data.remote.AccountDeleteRequestDto
import com.mybetrecord.android.data.remote.LoginRequestDto
import com.mybetrecord.android.data.remote.LogoutRequestDto
import com.mybetrecord.android.data.remote.PasswordResetConfirmDto
import com.mybetrecord.android.data.remote.PasswordResetRequestDto
import com.mybetrecord.android.data.remote.RefreshRequestDto
import com.mybetrecord.android.data.remote.RegisterRequestDto
import com.mybetrecord.android.data.remote.SettingsUpdateDto
import com.mybetrecord.android.data.remote.TokenResponseDto
import com.mybetrecord.android.data.remote.UserDto
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val api: AuthApi,
    private val tokenStore: TokenStore,
) {
    fun isLoggedIn(): Boolean = tokenStore.hasSession()

    suspend fun login(email: String, password: String): TokenResponseDto {
        val tokens = api.login(LoginRequestDto(email = email.trim(), password = password))
        persistTokens(tokens)
        return tokens
    }

    suspend fun register(email: String, password: String, timezone: String?): String {
        return api.register(
            RegisterRequestDto(
                email = email.trim(),
                password = password,
                timezone = timezone,
            ),
        ).message
    }

    suspend fun requestPasswordReset(email: String) {
        // Backend intentionally returns 200 whether or not the email exists, to avoid
        // leaking account existence. We don't branch on the response body here.
        api.requestPasswordReset(PasswordResetRequestDto(email = email.trim()))
    }

    suspend fun confirmPasswordReset(token: String, newPassword: String) {
        val response = api.confirmPasswordReset(
            PasswordResetConfirmDto(token = token.trim(), password = newPassword),
        )
        if (!response.isSuccessful) {
            throw IllegalStateException(
                if (response.code() == 400 || response.code() == 422) {
                    "That code is invalid or has expired. Request a new one."
                } else {
                    "Password reset failed (${response.code()})"
                },
            )
        }
    }

    /**
     * Refreshes tokens. Used by unit tests and can be called explicitly before critical flows.
     * Returns null when refresh fails (caller should clear session).
     */
    suspend fun refreshAccessToken(): TokenResponseDto? {
        val refresh = tokenStore.getRefreshToken() ?: return null
        return try {
            val tokens = api.refresh(RefreshRequestDto(refresh))
            persistTokens(tokens)
            tokens
        } catch (_: Exception) {
            tokenStore.clear()
            null
        }
    }

    suspend fun logout() {
        val refresh = tokenStore.getRefreshToken()
        try {
            if (!refresh.isNullOrBlank()) {
                api.logout(LogoutRequestDto(refreshToken = refresh))
            }
        } catch (_: Exception) {
            // Always clear local session even if network fails.
        } finally {
            tokenStore.clear()
        }
    }

    suspend fun me(): UserDto = api.me()

    suspend fun updateSettings(update: SettingsUpdateDto): UserDto = api.updateSettings(update)

    suspend fun deleteAccount(password: String) {
        val response = api.deleteAccount(
            AccountDeleteRequestDto(password = password, confirm = "DELETE"),
        )
        if (!response.isSuccessful) {
            throw IllegalStateException("Account deletion failed (${response.code()})")
        }
        tokenStore.clear()
    }

    fun persistTokens(tokens: TokenResponseDto) {
        tokenStore.setAccessToken(tokens.accessToken)
        tokens.refreshToken?.let { tokenStore.setRefreshToken(it) }
    }

    fun clearSession() = tokenStore.clear()
}

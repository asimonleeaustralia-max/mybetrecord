package com.mybetrecord.android.data.remote

import com.mybetrecord.android.data.local.TokenStore
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.Authenticator
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.Route
import java.util.concurrent.locks.ReentrantLock
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton
import kotlin.concurrent.withLock

/**
 * On HTTP 401, rotates the refresh token once and retries the original request.
 * Concurrent 401s share a single refresh via [lock].
 */
@Singleton
class TokenAuthenticator @Inject constructor(
    private val tokenStore: TokenStore,
    @Named("baseUrl") private val baseUrl: String,
    private val json: Json,
) : Authenticator {

    private val lock = ReentrantLock()

    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) return null
        val refresh = tokenStore.getRefreshToken() ?: return null

        return lock.withLock {
            val currentAccess = tokenStore.getAccessToken()
            val requestToken = response.request.header("Authorization")
                ?.removePrefix("Bearer ")
                ?.trim()
            // Another thread may have already refreshed.
            if (!currentAccess.isNullOrBlank() && currentAccess != requestToken) {
                return@withLock response.request.newBuilder()
                    .header("Authorization", "Bearer $currentAccess")
                    .build()
            }

            val refreshed = runBlocking { refreshTokens(refresh) } ?: run {
                tokenStore.clear()
                return@withLock null
            }

            tokenStore.setAccessToken(refreshed.accessToken)
            refreshed.refreshToken?.let { tokenStore.setRefreshToken(it) }

            response.request.newBuilder()
                .header("Authorization", "Bearer ${refreshed.accessToken}")
                .build()
        }
    }

    private fun refreshTokens(refreshToken: String): TokenResponseDto? {
        val client = OkHttpClient()
        val body = json.encodeToString(
            RefreshRequestDto.serializer(),
            RefreshRequestDto(refreshToken),
        ).toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/auth/refresh")
            .post(body)
            .header("Accept", "application/json")
            .build()
        client.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) return null
            val payload = resp.body?.string() ?: return null
            return json.decodeFromString(TokenResponseDto.serializer(), payload)
        }
    }

    private fun responseCount(response: Response): Int {
        var result = 1
        var prior = response.priorResponse
        while (prior != null) {
            result++
            prior = prior.priorResponse
        }
        return result
    }
}

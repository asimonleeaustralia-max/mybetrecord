package com.mybetrecord.android

import com.mybetrecord.android.data.local.TokenStore
import com.mybetrecord.android.data.remote.AuthApi
import com.mybetrecord.android.data.remote.RefreshRequestDto
import com.mybetrecord.android.data.remote.TokenResponseDto
import com.mybetrecord.android.data.repository.AuthRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.runs
import io.mockk.verify
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

class AuthRepositoryRefreshTest {
    private lateinit var api: AuthApi
    private lateinit var tokenStore: TokenStore
    private lateinit var repository: AuthRepository

    @Before
    fun setUp() {
        api = mockk()
        tokenStore = mockk(relaxed = true)
        repository = AuthRepository(
            api,
            tokenStore,
            mockk(relaxed = true),
            betDao = mockk(relaxed = true),
            pendingOpDao = mockk(relaxed = true),
            reportCacheDao = mockk(relaxed = true),
        )
    }

    @Test
    fun refreshAccessToken_persistsRotatedTokens() = runTest {
        every { tokenStore.getRefreshToken() } returns "old-refresh"
        coEvery { api.refresh(RefreshRequestDto("old-refresh")) } returns TokenResponseDto(
            accessToken = "new-access",
            expiresIn = 1800,
            refreshToken = "new-refresh",
            refreshExpiresIn = 2592000,
        )

        val result = repository.refreshAccessToken()

        assertEquals("new-access", result?.accessToken)
        assertEquals("new-refresh", result?.refreshToken)
        verify { tokenStore.setAccessToken("new-access") }
        verify { tokenStore.setRefreshToken("new-refresh") }
    }

    @Test
    fun refreshAccessToken_clearsSessionOnFailure() = runTest {
        every { tokenStore.getRefreshToken() } returns "stale-refresh"
        coEvery { api.refresh(any()) } throws RuntimeException("401")

        val result = repository.refreshAccessToken()

        assertNull(result)
        verify { tokenStore.clear() }
        coVerify(exactly = 1) { api.refresh(RefreshRequestDto("stale-refresh")) }
    }

    @Test
    fun refreshAccessToken_returnsNullWhenNoRefreshToken() = runTest {
        every { tokenStore.getRefreshToken() } returns null

        val result = repository.refreshAccessToken()

        assertNull(result)
        coVerify(exactly = 0) { api.refresh(any()) }
    }

    @Test
    fun persistTokens_storesAccessAndOptionalRefresh() {
        every { tokenStore.setAccessToken(any()) } just runs
        every { tokenStore.setRefreshToken(any()) } just runs

        repository.persistTokens(
            TokenResponseDto(
                accessToken = "access",
                expiresIn = 60,
                refreshToken = "refresh",
            ),
        )

        verify { tokenStore.setAccessToken("access") }
        verify { tokenStore.setRefreshToken("refresh") }
    }
}

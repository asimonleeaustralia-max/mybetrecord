package com.mybetrecord.android

import com.mybetrecord.android.data.local.TokenStore
import com.mybetrecord.android.data.remote.AuthApi
import com.mybetrecord.android.data.remote.PasswordResetConfirmDto
import com.mybetrecord.android.data.remote.PasswordResetRequestDto
import com.mybetrecord.android.data.repository.AuthRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

class AuthRepositoryPasswordResetTest {
    private lateinit var api: AuthApi
    private lateinit var tokenStore: TokenStore
    private lateinit var repository: AuthRepository

    @Before
    fun setUp() {
        api = mockk()
        tokenStore = mockk(relaxed = true)
        repository = AuthRepository(api, tokenStore, mockk(relaxed = true))
    }

    @Test
    fun requestPasswordReset_trimsEmailAndCallsApi() = runTest {
        coEvery { api.requestPasswordReset(any()) } returns Response.success(Unit)

        repository.requestPasswordReset("  user@example.com  ")

        coVerify { api.requestPasswordReset(PasswordResetRequestDto(email = "user@example.com")) }
    }

    @Test
    fun confirmPasswordReset_succeedsOnOkResponse() = runTest {
        coEvery { api.confirmPasswordReset(any()) } returns Response.success(Unit)

        repository.confirmPasswordReset(" 123456 ", "newSecurePassword1")

        coVerify {
            api.confirmPasswordReset(
                PasswordResetConfirmDto(token = "123456", password = "newSecurePassword1"),
            )
        }
    }

    @Test
    fun confirmPasswordReset_throwsUserFriendlyMessageOn422() = runTest {
        val errorBody = "{}".toResponseBody("application/json".toMediaType())
        coEvery { api.confirmPasswordReset(any()) } returns Response.error(422, errorBody)

        val exception = try {
            repository.confirmPasswordReset("bad-code", "newSecurePassword1")
            null
        } catch (t: IllegalStateException) {
            t
        }

        assertNotNull(exception)
        assertTrue(exception!!.message!!.contains("invalid or has expired"))
    }
}

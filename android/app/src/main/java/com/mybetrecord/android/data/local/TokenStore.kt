package com.mybetrecord.android.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Access token stays in memory. Refresh token is Keystore-backed via EncryptedSharedPreferences.
 */
@Singleton
class TokenStore @Inject constructor(
    @ApplicationContext context: Context,
) {
    @Volatile
    private var accessToken: String? = null

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun getAccessToken(): String? = accessToken

    fun setAccessToken(token: String?) {
        accessToken = token
    }

    fun getRefreshToken(): String? = prefs.getString(KEY_REFRESH, null)

    fun setRefreshToken(token: String?) {
        prefs.edit().apply {
            if (token == null) remove(KEY_REFRESH) else putString(KEY_REFRESH, token)
            apply()
        }
    }

    fun clear() {
        accessToken = null
        prefs.edit().remove(KEY_REFRESH).apply()
    }

    fun hasSession(): Boolean = !getRefreshToken().isNullOrBlank() || !accessToken.isNullOrBlank()

    companion object {
        const val PREFS_NAME = "mbr_secure_prefs"
        private const val KEY_REFRESH = "refresh_token"
    }
}

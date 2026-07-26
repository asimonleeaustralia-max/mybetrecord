package com.mybetrecord.android.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.runBlocking
import javax.inject.Inject
import javax.inject.Singleton

private val Context.appPrefsDataStore: DataStore<Preferences> by preferencesDataStore("mbr_app_prefs")

@Singleton
class AppPreferences @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val ageKey = booleanPreferencesKey("age_attested")
    private val localeKey = stringPreferencesKey("locale")

    val ageAttested: Flow<Boolean> = context.appPrefsDataStore.data.map { prefs ->
        prefs[ageKey] == true
    }

    suspend fun setAgeAttested(value: Boolean) {
        context.appPrefsDataStore.edit { it[ageKey] = value }
    }

    /** Blocking read used once at startup, before the first frame needs strings. */
    fun getLocaleBlocking(): String? = runBlocking {
        context.appPrefsDataStore.data.first()[localeKey]
    }

    suspend fun setLocale(value: String) {
        context.appPrefsDataStore.edit { it[localeKey] = value }
    }
}

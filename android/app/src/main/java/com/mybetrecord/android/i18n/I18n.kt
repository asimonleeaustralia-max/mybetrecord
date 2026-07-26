package com.mybetrecord.android.i18n

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.util.Locale

/**
 * Runtime string catalog shared with the web app.
 *
 * The Android app bundles the same locale JSON files the web frontend serves from
 * /app/locales, so both clients stay translated in lockstep (~100 languages).
 * Keys are dotted paths ("form.sport"); missing keys fall back to English, then
 * to the key itself. [locale] is Compose state, so any composable that calls
 * [t] recomposes when the language changes.
 */
object I18n {
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private lateinit var appContext: Context
    private var en: Map<String, String> = emptyMap()
    private var current: Map<String, String> = emptyMap()

    /** Ordered top-20 codes followed by the rest, from languages.json. */
    var languages: List<Pair<String, String>> = emptyList()
        private set

    var locale: String by mutableStateOf("en")
        private set

    // Strings the Android app needs that have no web equivalent. English-only;
    // they fall back here for every locale.
    private val androidExtras = mapOf(
        "android.home" to "Home",
        "android.tools" to "Tools",
        "android.toolsSub" to "Stake and liability calculators — nothing here places a bet.",
        "android.kellyTitle" to "Kelly stake calculator",
        "android.kellyOdds" to "Bookmaker odds (decimal)",
        "android.kellyImplied" to "Your implied odds (decimal)",
        "android.liabilityTitle" to "Lay liability calculator",
        "android.layOdds" to "Lay odds (decimal)",
        "android.exportShare" to "Export & share",
        "android.exporting" to "Preparing export…",
        "android.shareProfile" to "Share public profile link",
        "android.deleteForever" to "Delete forever",
        "android.deleteAccountBody" to "This permanently deletes your account and bet history. Type DELETE to confirm.",
        "android.typeDelete" to "Type DELETE",
        "android.planWebNote" to "Plan changes are managed on the website. This app does not sell subscriptions.",
        "android.eventAtHint" to "YYYY-MM-DD HH:MM (optional)",
        "android.invalidEventAt" to "Event date/time must look like 2026-07-26 19:30",
        "android.requiredFields" to "Event, selection, odds and stake are required",
        "android.invalidFractional" to "Fractional odds must look like 11/8",
        "android.closingOdds" to "Closing odds (decimal, for CLV)",
        "android.summarySub" to "Summary metrics from your recorded bets.",
        "android.language" to "Language",
        "android.turnover" to "Turnover",
        "android.legalHelp" to "Legal & help",
        "android.resetCode" to "Reset code",
        "android.resendCode" to "Resend code",
        "android.resendCodeIn" to "Resend code in {{s}}s",
        "android.useDifferentEmail" to "Use a different email",
        "android.signInNewPassword" to "You can now sign in with your new password.",
    )

    fun init(context: Context, savedLocale: String?) {
        appContext = context.applicationContext
        loadCatalog()
        en = loadStrings("en") ?: emptyMap()
        val target = normalize(savedLocale) ?: systemLocale()
        applyLocale(target)
    }

    /** Best supported match for the device language, mirroring the web's browserLocale(). */
    fun systemLocale(): String {
        val tag = Locale.getDefault().toLanguageTag()
        return normalize(tag) ?: "en"
    }

    fun switchLocale(code: String) {
        applyLocale(normalize(code) ?: "en")
    }

    private fun applyLocale(code: String) {
        current = if (code == "en") en else loadStrings(code) ?: en
        locale = code
    }

    fun t(key: String, vars: Map<String, String> = emptyMap()): String {
        // Read the state so composables calling t() recompose on language change.
        val active = locale
        val raw = current[key] ?: en[key] ?: androidExtras[key] ?: key
        if (vars.isEmpty()) return raw
        return vars.entries.fold(raw) { acc, (k, v) -> acc.replace("{{$k}}", v) }
    }

    fun displayName(code: String): String =
        languages.firstOrNull { it.first == code }?.second ?: code

    /** Mirrors the web's normalizeLocale(): exact match, case-insensitive, then base language. */
    fun normalize(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        val codes = languages.map { it.first }.ifEmpty { listOf("en") }
        val tag = raw.trim().replace('_', '-')
        codes.firstOrNull { it == tag }?.let { return it }
        val lower = tag.lowercase()
        codes.firstOrNull { it.lowercase() == lower }?.let { return it }
        val base = lower.substringBefore('-')
        if (base == "zh") {
            val traditional = Regex("hant|tw|hk|mo", RegexOption.IGNORE_CASE).containsMatchIn(tag)
            return if (traditional) codes.firstOrNull { it == "zh-TW" } else codes.firstOrNull { it == "zh-CN" }
        }
        return codes.firstOrNull { it.lowercase() == base || it.lowercase().startsWith("$base-") }
    }

    private fun loadCatalog() {
        val obj = readAsset("locales/languages.json") ?: return
        val all = obj["all"]?.jsonObject ?: return
        val top = (obj["top20"] as? kotlinx.serialization.json.JsonArray)
            ?.mapNotNull { it.jsonPrimitive.content }
            ?: emptyList()
        val rest = all.keys.filter { it !in top }.sortedBy { all[it]!!.jsonPrimitive.content.lowercase() }
        languages = (top + rest).mapNotNull { code ->
            all[code]?.jsonPrimitive?.content?.let { code to it }
        }
    }

    private fun loadStrings(code: String): Map<String, String>? {
        val obj = readAsset("locales/$code.json") ?: return null
        val flat = mutableMapOf<String, String>()
        flatten(obj, "", flat)
        return flat
    }

    private fun readAsset(path: String): JsonObject? = try {
        appContext.assets.open(path).bufferedReader().use { reader ->
            json.parseToJsonElement(reader.readText()).jsonObject
        }
    } catch (_: Exception) {
        null
    }

    private fun flatten(obj: JsonObject, prefix: String, into: MutableMap<String, String>) {
        for ((k, v) in obj) {
            val key = if (prefix.isEmpty()) k else "$prefix.$k"
            when (v) {
                is JsonObject -> flatten(v, key, into)
                else -> into[key] = v.jsonPrimitive.content
            }
        }
    }
}

/** Shorthand used across screens. */
fun tr(key: String, vars: Map<String, String> = emptyMap()): String = I18n.t(key, vars)

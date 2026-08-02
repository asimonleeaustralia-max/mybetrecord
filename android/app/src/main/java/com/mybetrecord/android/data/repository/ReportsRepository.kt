package com.mybetrecord.android.data.repository

import com.mybetrecord.android.data.local.ReportCacheDao
import com.mybetrecord.android.data.local.ReportCacheEntity
import com.mybetrecord.android.data.remote.BreakdownRowDto
import com.mybetrecord.android.data.remote.EquityPointDto
import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.remote.ReportsApi
import kotlinx.serialization.KSerializer
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * The filter set the web app's reports page exposes. Blank values mean "all",
 * matching the empty <select> options there.
 */
data class ReportFilters(
    val sport: String = "",
    val betType: String = "",
    val tipster: String = "",
    val currency: String = "",
    /** ISO dates (yyyy-MM-dd), as the backend's date_from/date_to expect. */
    val dateFrom: String = "",
    val dateTo: String = "",
) {
    fun toQuery(): Map<String, String> = buildMap {
        if (sport.isNotBlank()) put("sport", sport)
        if (betType.isNotBlank()) put("bet_type", betType)
        if (tipster.isNotBlank()) put("tipster", tipster)
        if (currency.isNotBlank()) put("currency", currency)
        if (dateFrom.isNotBlank()) put("date_from", dateFrom)
        if (dateTo.isNotBlank()) put("date_to", dateTo)
    }

    /** Stable cache key for this filter combination. */
    fun cacheKey(): String = toQuery().toSortedMap().entries.joinToString("&") { "${it.key}=${it.value}" }
}

/**
 * A report payload plus where it came from. [fetchedAt] is when the server last
 * answered, so the screen can say how stale an offline view is.
 */
data class Cached<T>(
    val value: T,
    val fromCache: Boolean,
    val fetchedAt: Long?,
)

@Singleton
class ReportsRepository @Inject constructor(
    private val api: ReportsApi,
    private val cacheDao: ReportCacheDao,
    private val json: Json,
) {
    /**
     * Without an explicit currency filter the summary is reported in the user's
     * dominant currency, so mixed-currency ledgers never add up nonsensically.
     */
    suspend fun summary(filters: ReportFilters = ReportFilters()): Cached<ReportSummaryDto> =
        fetchOrCached(
            key = "summary:${filters.cacheKey()}",
            serializer = ReportSummaryDto.serializer(),
        ) { api.summary(filters.toQuery() + ("use_primary_currency" to "true")) }

    suspend fun equityCurve(filters: ReportFilters): Cached<List<EquityPointDto>> =
        fetchOrCached(
            key = "equity:${filters.cacheKey()}",
            serializer = ListSerializer(EquityPointDto.serializer()),
        ) { api.equityCurve(filters.toQuery()) }

    suspend fun breakdown(dimension: String, filters: ReportFilters): Cached<List<BreakdownRowDto>> =
        fetchOrCached(
            key = "breakdown:$dimension:${filters.cacheKey()}",
            serializer = ListSerializer(BreakdownRowDto.serializer()),
        ) { api.breakdown(dimension, filters.toQuery()) }

    /**
     * Warms the cache for the default view so Reports still renders after going
     * offline, even if the user never opened the page while connected.
     */
    suspend fun prefetch(filters: ReportFilters = ReportFilters()) {
        runCatching { summary(filters) }
        runCatching { equityCurve(filters) }
        // Only the default dimension: the others are one tap and rarely needed cold.
        runCatching { breakdown("sport", filters) }
        // Home asks for the unfiltered summary, which is a different cache key.
        if (filters != ReportFilters()) {
            runCatching { summary(ReportFilters()) }
        }
    }

    suspend fun clearCache() = cacheDao.clear()

    /**
     * Calls the API and records the result; on a connection failure falls back
     * to the last good copy. A missing cache entry rethrows, so the screen can
     * explain that this view has never been downloaded.
     */
    private suspend fun <T> fetchOrCached(
        key: String,
        serializer: KSerializer<T>,
        fetch: suspend () -> T,
    ): Cached<T> {
        return try {
            val fresh = fetch()
            cacheDao.upsert(ReportCacheEntity(key = key, payloadJson = json.encodeToString(serializer, fresh)))
            Cached(fresh, fromCache = false, fetchedAt = System.currentTimeMillis())
        } catch (e: IOException) {
            val entry = cacheDao.get(key) ?: throw e
            val decoded = try {
                json.decodeFromString(serializer, entry.payloadJson)
            } catch (_: Exception) {
                throw e
            }
            Cached(decoded, fromCache = true, fetchedAt = entry.fetchedAt)
        }
    }
}

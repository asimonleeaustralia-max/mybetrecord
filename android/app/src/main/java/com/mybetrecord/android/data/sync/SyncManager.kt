package com.mybetrecord.android.data.sync

import com.mybetrecord.android.data.local.NetworkMonitor
import com.mybetrecord.android.data.local.PendingOpDao
import com.mybetrecord.android.data.local.PendingOpType
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.remote.BetsApi
import com.mybetrecord.android.data.repository.AuthRepository
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.data.repository.ReportFilters
import com.mybetrecord.android.data.repository.ReportsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Replays writes made while offline and keeps a copy of the reports data on
 * device.
 *
 * Ops replay strictly in order: an out-of-order update would hit a bet the
 * server has not created yet. A network failure stops the drain and leaves the
 * queue intact for the next time connectivity returns; a rejection from the
 * server (4xx) is terminal and gets flagged rather than retried forever.
 */
@Singleton
class SyncManager @Inject constructor(
    private val api: BetsApi,
    private val betsRepository: BetsRepository,
    private val reportsRepository: ReportsRepository,
    private val authRepository: AuthRepository,
    private val pendingOpDao: PendingOpDao,
    private val networkMonitor: NetworkMonitor,
    private val json: Json,
) {
    private val _syncing = MutableStateFlow(false)
    val syncing: StateFlow<Boolean> = _syncing.asStateFlow()

    // One drain at a time, so a reconnect mid-sync cannot double-post a create.
    private val mutex = Mutex()

    /** Starts watching connectivity; called once from the Application. */
    fun start(scope: CoroutineScope) {
        scope.launch {
            networkMonitor.isOnline
                .distinctUntilChanged()
                .filter { it }
                .collect { syncNow() }
        }
    }

    suspend fun syncNow() {
        // Every call needs a token, so there is nothing to do while signed out.
        if (!authRepository.isLoggedIn()) return
        if (!networkMonitor.currentlyOnline()) return
        mutex.withLock {
            _syncing.value = true
            try {
                val drained = drainOutbox()
                // Refresh from the server so locally-computed P/L is replaced by
                // the authoritative values, then re-warm the offline report data.
                if (drained) runCatching { betsRepository.refreshBets() }
                runCatching { reportsRepository.prefetch(defaultReportFilters()) }
            } finally {
                _syncing.value = false
            }
        }
    }

    /**
     * The filters the Reports screen opens with, so what we cache is what the
     * screen will ask for. Mirrors ReportsViewModel's currency default.
     */
    private suspend fun defaultReportFilters(): ReportFilters {
        val options = runCatching { betsRepository.filterOptions() }.getOrNull()
        return ReportFilters(currency = options?.currencies?.firstOrNull().orEmpty())
    }

    /** Returns true when at least one queued op reached the server. */
    private suspend fun drainOutbox(): Boolean {
        var progressed = false
        for (op in pendingOpDao.pending()) {
            try {
                when (op.type) {
                    PendingOpType.CREATE -> {
                        val body = json.decodeFromString(BetCreateDto.serializer(), op.payloadJson)
                        val created = api.createBet(body)
                        betsRepository.replaceLocalBet(op.betId, created)
                    }
                    PendingOpType.UPDATE -> {
                        val body = json.decodeFromString(BetUpdateDto.serializer(), op.payloadJson)
                        betsRepository.cacheServerBet(api.updateBet(op.betId, body))
                    }
                    PendingOpType.DELETE -> {
                        val response = api.deleteBet(op.betId)
                        // A 404 means it is already gone — that is still success.
                        if (!response.isSuccessful && response.code() !in listOf(204, 404)) {
                            throw HttpException(response)
                        }
                    }
                }
                pendingOpDao.delete(op.id)
                progressed = true
            } catch (e: IOException) {
                // Connection dropped again — stop and keep the rest queued.
                return progressed
            } catch (e: HttpException) {
                if (e.code() in 400..499 && e.code() != 408 && e.code() != 429) {
                    // The server will never accept this; flag it instead of looping.
                    pendingOpDao.markFailed(op.id, "HTTP ${e.code()}")
                    progressed = true
                } else {
                    return progressed
                }
            } catch (e: Exception) {
                pendingOpDao.markFailed(op.id, e.message)
                progressed = true
            }
        }
        return progressed
    }
}

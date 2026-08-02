package com.mybetrecord.android

import com.mybetrecord.android.data.local.BetDao
import com.mybetrecord.android.data.local.BetEntity
import com.mybetrecord.android.data.local.PendingOpDao
import com.mybetrecord.android.data.local.PendingOpEntity
import com.mybetrecord.android.data.local.PendingOpType
import com.mybetrecord.android.data.local.ReportCacheDao
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.remote.BetsApi
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.data.repository.isLocalBetId
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.slot
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.IOException

/**
 * Behaviour of the offline write queue: a lost connection must never lose a
 * change, and must never leave the ledger showing something the user did not do.
 */
class OfflineOutboxTest {
    private lateinit var api: BetsApi
    private lateinit var betDao: BetDao
    private lateinit var pendingOpDao: PendingOpDao
    private lateinit var cacheDao: ReportCacheDao
    private lateinit var repository: BetsRepository
    private val json = Json { ignoreUnknownKeys = true; isLenient = true; explicitNulls = false }

    @Before
    fun setUp() {
        api = mockk()
        betDao = mockk(relaxed = true)
        pendingOpDao = mockk(relaxed = true)
        cacheDao = mockk(relaxed = true)
        repository = BetsRepository(api, betDao, pendingOpDao, cacheDao, json)
    }

    private fun sampleCreate() = BetCreateDto(
        sport = "Darts",
        event = "Littler vs Rock",
        selection = "Littler over 11.5 180s",
        odds = 2.0,
        stake = 50.0,
        currency = "AUD",
        outcome = "pending",
    )

    private fun cachedBet(id: String, outcome: String = "pending", profit: Double = 0.0): BetEntity {
        val dto = BetDto(
            id = id,
            event = "Littler vs Rock",
            selection = "Littler over 11.5 180s",
            sport = "Darts",
            placedAt = "2026-08-02T10:00:00",
            oddsDecimal = 2.0,
            stake = 50.0,
            currency = "AUD",
            outcome = outcome,
            profit = profit,
        )
        return BetEntity(
            id = id,
            event = dto.event,
            selection = dto.selection,
            sport = dto.sport,
            betType = dto.betType,
            oddsDecimal = dto.oddsDecimal,
            stake = dto.stake,
            currency = dto.currency,
            outcome = dto.outcome,
            profit = dto.profit,
            placedAt = dto.placedAt,
            bookmaker = null,
            payloadJson = json.encodeToString(BetDto.serializer(), dto),
        )
    }

    @Test
    fun createOffline_queuesTheWriteAndShowsTheBetImmediately() = runTest {
        coEvery { api.createBet(any()) } throws IOException("dead spot")
        val cached = slot<BetEntity>()
        val queued = slot<PendingOpEntity>()
        coEvery { betDao.upsert(capture(cached)) } returns Unit
        coEvery { pendingOpDao.upsert(capture(queued)) } returns 1L

        val result = repository.createBet(sampleCreate())

        // The user sees their bet straight away, flagged as not yet synced.
        assertTrue(isLocalBetId(result.id))
        assertTrue(result.pendingSync)
        assertTrue(cached.captured.pendingSync)
        // And the write is durable, pointed at the same local id.
        assertEquals(PendingOpType.CREATE, queued.captured.type)
        assertEquals(result.id, queued.captured.betId)
    }

    @Test
    fun createOnline_doesNotQueueAnything() = runTest {
        val server = BetDto(
            id = "server-1",
            event = "Littler vs Rock",
            selection = "Littler over 11.5 180s",
            sport = "Darts",
            placedAt = "2026-08-02T10:00:00",
            oddsDecimal = 2.0,
            stake = 50.0,
        )
        coEvery { api.createBet(any()) } returns server

        val result = repository.createBet(sampleCreate())

        assertEquals("server-1", result.id)
        assertFalse(result.pendingSync)
        coVerify(exactly = 0) { pendingOpDao.upsert(any()) }
    }

    @Test
    fun settlingOffline_recomputesProfitLocally() = runTest {
        coEvery { api.updateBet(any(), any()) } throws IOException("dead spot")
        coEvery { betDao.getById("server-1") } returns cachedBet("server-1")
        coEvery { pendingOpDao.findFor(any(), any()) } returns null
        val cached = slot<BetEntity>()
        coEvery { betDao.upsert(capture(cached)) } returns Unit

        val result = repository.setOutcome("server-1", "win")

        // 50 stake at 2.0 → 50 profit, so the ledger stays believable offline.
        assertEquals("win", result.outcome)
        assertEquals(50.0, result.profit, 1e-9)
        assertTrue(cached.captured.pendingSync)
    }

    @Test
    fun repeatedOfflineEdits_collapseIntoOneQueuedUpdate() = runTest {
        coEvery { api.updateBet(any(), any()) } throws IOException("dead spot")
        coEvery { betDao.getById("server-1") } returns cachedBet("server-1")
        val existing = PendingOpEntity(
            id = 7,
            betId = "server-1",
            type = PendingOpType.UPDATE,
            payloadJson = json.encodeToString(BetUpdateDto.serializer(), BetUpdateDto(outcome = "win")),
        )
        coEvery { pendingOpDao.findFor("server-1", PendingOpType.UPDATE) } returns existing
        val queued = slot<PendingOpEntity>()
        coEvery { pendingOpDao.upsert(capture(queued)) } returns 7L

        repository.updateBet("server-1", BetUpdateDto(notes = "changed my mind"))

        // Same row is rewritten, not a second op, and the earlier field survives.
        assertEquals(7L, queued.captured.id)
        val merged = json.decodeFromString(BetUpdateDto.serializer(), queued.captured.payloadJson)
        assertEquals("win", merged.outcome)
        assertEquals("changed my mind", merged.notes)
    }

    @Test
    fun editingABetCreatedOffline_foldsIntoTheQueuedCreate() = runTest {
        val localId = "local-abc"
        coEvery { betDao.getById(localId) } returns cachedBet(localId)
        val create = PendingOpEntity(
            id = 3,
            betId = localId,
            type = PendingOpType.CREATE,
            payloadJson = json.encodeToString(BetCreateDto.serializer(), sampleCreate()),
        )
        coEvery { pendingOpDao.findFor(localId, PendingOpType.CREATE) } returns create
        val queued = slot<PendingOpEntity>()
        coEvery { pendingOpDao.upsert(capture(queued)) } returns 3L

        repository.setOutcome(localId, "win")

        // No update op is queued — the server has no such id yet.
        val folded = json.decodeFromString(BetCreateDto.serializer(), queued.captured.payloadJson)
        assertEquals(PendingOpType.CREATE, queued.captured.type)
        assertEquals("win", folded.outcome)
        coVerify(exactly = 0) { api.updateBet(any(), any()) }
    }

    @Test
    fun deletingABetCreatedOffline_justDropsTheQueuedCreate() = runTest {
        val localId = "local-abc"

        repository.deleteBet(localId)

        coVerify { pendingOpDao.deleteForBet(localId) }
        coVerify { betDao.delete(localId) }
        // Nothing to tell the server about — it never saw this bet.
        coVerify(exactly = 0) { api.deleteBet(any()) }
    }

    @Test
    fun deletingOffline_supersedesEarlierQueuedEdits() = runTest {
        coEvery { api.deleteBet("server-1") } throws IOException("dead spot")
        val queued = slot<PendingOpEntity>()
        coEvery { pendingOpDao.upsert(capture(queued)) } returns 1L

        repository.deleteBet("server-1")

        coVerify { pendingOpDao.deleteForBet("server-1") }
        assertEquals(PendingOpType.DELETE, queued.captured.type)
        coVerify { betDao.delete("server-1") }
    }

    @Test
    fun refreshingOffline_keepsQueuedRows() = runTest {
        coEvery { api.listBets(any(), any()) } returns emptyList()

        repository.refreshBets()

        // Only server-owned rows are cleared; pending work is never discarded.
        coVerify { betDao.clearSynced() }
        coVerify(exactly = 0) { betDao.clear() }
    }
}

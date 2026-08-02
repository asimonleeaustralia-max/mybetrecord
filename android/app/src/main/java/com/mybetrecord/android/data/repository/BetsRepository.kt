package com.mybetrecord.android.data.repository

import com.mybetrecord.android.data.local.BetDao
import com.mybetrecord.android.data.local.BetEntity
import com.mybetrecord.android.data.local.PendingOpDao
import com.mybetrecord.android.data.local.PendingOpEntity
import com.mybetrecord.android.data.local.PendingOpType
import com.mybetrecord.android.data.local.ReportCacheDao
import com.mybetrecord.android.data.local.ReportCacheEntity
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.data.remote.BetLegDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.remote.BetsApi
import com.mybetrecord.android.util.BetMath
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.IOException
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
data class BetFilterOptions(
    val sports: List<String> = emptyList(),
    val betTypes: List<String> = emptyList(),
    val tipsters: List<String> = emptyList(),
    val currencies: List<String> = emptyList(),
) {
    val isEmpty: Boolean
        get() = sports.isEmpty() && betTypes.isEmpty() && tipsters.isEmpty() && currencies.isEmpty()
}

private const val FILTER_OPTIONS_KEY = "filter_options"

/** Ids minted on-device for bets recorded with no connection. */
private const val LOCAL_ID_PREFIX = "local-"

fun isLocalBetId(id: String): Boolean = id.startsWith(LOCAL_ID_PREFIX)

@Singleton
class BetsRepository @Inject constructor(
    private val api: BetsApi,
    private val betDao: BetDao,
    private val pendingOpDao: PendingOpDao,
    private val cacheDao: ReportCacheDao,
    private val json: Json,
) {
    fun observeCachedBets(): Flow<List<BetDto>> =
        betDao.observeBets().map { rows -> rows.mapNotNull { decode(it) } }

    /** Bets the user has changed that the server has not accepted yet. */
    fun observePendingCount(): Flow<Int> = pendingOpDao.observePendingCount()

    fun observeFailedCount(): Flow<Int> = pendingOpDao.observeFailedCount()

    suspend fun refreshBets(): List<BetDto> {
        val remote = api.listBets()
        // Drop only rows the server owns; anything still queued locally stays put.
        betDao.clearSynced()
        betDao.upsertAll(remote.map { encode(it) })
        return remote
    }

    suspend fun getBet(id: String): BetDto {
        // A locally created bet does not exist upstream yet.
        if (isLocalBetId(id)) {
            return betDao.getById(id)?.let { decode(it) }
                ?: throw IllegalStateException("Bet not found")
        }
        return try {
            val remote = api.getBet(id)
            // Never clobber a local edit that is still waiting to sync.
            if (betDao.getById(id)?.pendingSync == true) {
                betDao.getById(id)?.let { decode(it) } ?: remote
            } else {
                betDao.upsert(encode(remote))
                remote
            }
        } catch (e: Exception) {
            betDao.getById(id)?.let { decode(it) } ?: throw e
        }
    }

    suspend fun createBet(body: BetCreateDto): BetDto {
        return try {
            val created = api.createBet(body)
            betDao.upsert(encode(created))
            created
        } catch (e: IOException) {
            // No connection: show it straight away and replay the create later.
            val localId = LOCAL_ID_PREFIX + UUID.randomUUID()
            val optimistic = body.toOptimisticBet(localId)
            betDao.upsert(encode(optimistic, pendingSync = true))
            pendingOpDao.upsert(
                PendingOpEntity(
                    betId = localId,
                    type = PendingOpType.CREATE,
                    payloadJson = json.encodeToString(body),
                ),
            )
            optimistic
        }
    }

    suspend fun updateBet(id: String, body: BetUpdateDto): BetDto {
        // Bets created offline have no server id, so fold edits into the
        // queued create instead of queuing an update the server can't route.
        if (isLocalBetId(id)) return updateQueuedCreate(id, body)

        return try {
            val updated = api.updateBet(id, body)
            betDao.upsert(encode(updated))
            updated
        } catch (e: IOException) {
            val cached = betDao.getById(id)?.let { decode(it) } ?: throw e
            val merged = cached.applying(body)
            betDao.upsert(encode(merged, pendingSync = true))
            // Collapse repeated edits of the same bet into one queued update.
            val existing = pendingOpDao.findFor(id, PendingOpType.UPDATE)
            val payload = existing?.let { mergeUpdates(it.payloadJson, body) } ?: body
            pendingOpDao.upsert(
                PendingOpEntity(
                    id = existing?.id ?: 0,
                    betId = id,
                    type = PendingOpType.UPDATE,
                    payloadJson = json.encodeToString(payload),
                ),
            )
            merged
        }
    }

    /** Settles a bet straight from the ledger, like the web row's result select. */
    suspend fun setOutcome(id: String, outcome: String): BetDto =
        updateBet(id, BetUpdateDto(outcome = outcome))

    suspend fun deleteBet(id: String) {
        // Deleting something that never reached the server just drops the queue entry.
        if (isLocalBetId(id)) {
            pendingOpDao.deleteForBet(id)
            betDao.delete(id)
            return
        }
        try {
            val response = api.deleteBet(id)
            if (!response.isSuccessful && response.code() != 204) {
                throw IllegalStateException("Delete failed (${response.code()})")
            }
            pendingOpDao.deleteForBet(id)
            betDao.delete(id)
        } catch (e: IOException) {
            // Supersede any queued edits — the bet is going away regardless.
            pendingOpDao.deleteForBet(id)
            pendingOpDao.upsert(
                PendingOpEntity(betId = id, type = PendingOpType.DELETE, payloadJson = ""),
            )
            betDao.delete(id)
        }
    }

    private suspend fun updateQueuedCreate(localId: String, body: BetUpdateDto): BetDto {
        val cached = betDao.getById(localId)?.let { decode(it) }
            ?: throw IllegalStateException("Bet not found")
        val merged = cached.applying(body)
        betDao.upsert(encode(merged, pendingSync = true))

        val op = pendingOpDao.findFor(localId, PendingOpType.CREATE)
        if (op != null) {
            val create = json.decodeFromString(BetCreateDto.serializer(), op.payloadJson)
            pendingOpDao.upsert(op.copy(payloadJson = json.encodeToString(create.applying(body))))
        }
        return merged
    }

    private fun mergeUpdates(existingJson: String, incoming: BetUpdateDto): BetUpdateDto {
        val prior = json.decodeFromString(BetUpdateDto.serializer(), existingJson)
        // Later edits win field by field; untouched fields keep the earlier value.
        return BetUpdateDto(
            sport = incoming.sport ?: prior.sport,
            event = incoming.event ?: prior.event,
            selection = incoming.selection ?: prior.selection,
            odds = incoming.odds ?: prior.odds,
            stake = incoming.stake ?: prior.stake,
            betType = incoming.betType ?: prior.betType,
            side = incoming.side ?: prior.side,
            currency = incoming.currency ?: prior.currency,
            oddsFormat = incoming.oddsFormat ?: prior.oddsFormat,
            oddsDenominator = incoming.oddsDenominator ?: prior.oddsDenominator,
            outcome = incoming.outcome ?: prior.outcome,
            tournament = incoming.tournament ?: prior.tournament,
            bookmaker = incoming.bookmaker ?: prior.bookmaker,
            portal = incoming.portal ?: prior.portal,
            tipster = incoming.tipster ?: prior.tipster,
            notes = incoming.notes ?: prior.notes,
            eachWay = incoming.eachWay ?: prior.eachWay,
            placed = incoming.placed ?: prior.placed,
            freeBet = incoming.freeBet ?: prior.freeBet,
            isMultiple = incoming.isMultiple ?: prior.isMultiple,
            legs = incoming.legs ?: prior.legs,
            cashOutAmount = incoming.cashOutAmount ?: prior.cashOutAmount,
            closingOdds = incoming.closingOdds ?: prior.closingOdds,
            eventAt = incoming.eventAt ?: prior.eventAt,
        )
    }

    /** Replaces a synced local row with the server's copy once a create lands. */
    suspend fun replaceLocalBet(localId: String, remote: BetDto) {
        betDao.delete(localId)
        betDao.upsert(encode(remote))
    }

    suspend fun cacheServerBet(bet: BetDto) = betDao.upsert(encode(bet))

    suspend fun createShareLink(id: String): String {
        val token = api.createShareLink(id).shareToken
        refreshCachedBet(id)
        return token
    }

    suspend fun revokeShareLink(id: String) {
        val response = api.revokeShareLink(id)
        if (!response.isSuccessful && response.code() != 204) {
            throw IllegalStateException("Revoke failed (${response.code()})")
        }
        refreshCachedBet(id)
    }

    /**
     * Distinct values behind the reports filters, fetched together. Each list is
     * best-effort: a failing lookup just leaves that filter offering "All".
     *
     * The result is cached because the Reports screen derives its default
     * currency from it — without a cached copy an offline load would fall back
     * to different filters, and so miss the report data prefetched for the
     * filters the screen normally uses.
     */
    suspend fun filterOptions(): BetFilterOptions {
        val fetched = coroutineScope {
            val sports = async { runCatching { api.sports() }.getOrDefault(emptyList()) }
            val betTypes = async { runCatching { api.betTypes() }.getOrDefault(emptyList()) }
            val tipsters = async { runCatching { api.tipsters() }.getOrDefault(emptyList()) }
            val currencies = async { runCatching { api.currencies() }.getOrDefault(emptyList()) }
            BetFilterOptions(sports.await(), betTypes.await(), tipsters.await(), currencies.await())
        }
        if (!fetched.isEmpty) {
            cacheDao.upsert(
                ReportCacheEntity(
                    key = FILTER_OPTIONS_KEY,
                    payloadJson = json.encodeToString(fetched),
                ),
            )
            return fetched
        }
        // Nothing came back — offline, or genuinely no bets yet.
        val cached = cacheDao.get(FILTER_OPTIONS_KEY) ?: return fetched
        return runCatching {
            json.decodeFromString(BetFilterOptions.serializer(), cached.payloadJson)
        }.getOrDefault(fetched)
    }

    private suspend fun refreshCachedBet(id: String) {
        try {
            betDao.upsert(encode(api.getBet(id)))
        } catch (_: Exception) {
            // Cache refresh is best-effort; the share call itself already succeeded.
        }
    }

    private fun encode(bet: BetDto, pendingSync: Boolean = false): BetEntity = BetEntity(
        id = bet.id,
        event = bet.event,
        selection = bet.selection,
        sport = bet.sport,
        betType = bet.betType,
        oddsDecimal = bet.oddsDecimal,
        stake = bet.stake,
        currency = bet.currency,
        outcome = bet.outcome,
        profit = bet.profit,
        placedAt = bet.placedAt,
        bookmaker = bet.bookmaker,
        payloadJson = json.encodeToString(bet),
        pendingSync = pendingSync,
    )

    private fun decode(entity: BetEntity): BetDto? = try {
        json.decodeFromString(BetDto.serializer(), entity.payloadJson)
            .copy(pendingSync = entity.pendingSync)
    } catch (_: Exception) {
        BetDto(
            id = entity.id,
            event = entity.event,
            selection = entity.selection,
            sport = entity.sport,
            betType = entity.betType,
            oddsDecimal = entity.oddsDecimal,
            stake = entity.stake,
            currency = entity.currency,
            outcome = entity.outcome,
            profit = entity.profit,
            placedAt = entity.placedAt,
            bookmaker = entity.bookmaker,
            pendingSync = entity.pendingSync,
        )
    }
}

/** Applies a queued edit on top of an offline create, so both replay as one call. */
private fun BetCreateDto.applying(u: BetUpdateDto): BetCreateDto = copy(
    sport = u.sport ?: sport,
    event = u.event ?: event,
    selection = u.selection ?: selection,
    odds = u.odds ?: odds,
    stake = u.stake ?: stake,
    betType = u.betType ?: betType,
    side = u.side ?: side,
    currency = u.currency ?: currency,
    oddsFormat = u.oddsFormat ?: oddsFormat,
    oddsDenominator = u.oddsDenominator ?: oddsDenominator,
    outcome = u.outcome ?: outcome,
    tournament = u.tournament ?: tournament,
    bookmaker = u.bookmaker ?: bookmaker,
    portal = u.portal ?: portal,
    tipster = u.tipster ?: tipster,
    notes = u.notes ?: notes,
    eachWay = u.eachWay ?: eachWay,
    placed = u.placed ?: placed,
    freeBet = u.freeBet ?: freeBet,
    isMultiple = u.isMultiple ?: isMultiple,
    legs = u.legs ?: legs,
    cashOutAmount = u.cashOutAmount ?: cashOutAmount,
    closingOdds = u.closingOdds ?: closingOdds,
    eventAt = u.eventAt ?: eventAt,
)

/**
 * Local preview of an edited bet. P/L is recomputed on-device so the ledger and
 * offline reports stay believable until the server settles it for real.
 */
private fun BetDto.applying(u: BetUpdateDto): BetDto {
    val next = copy(
        sport = u.sport ?: sport,
        event = u.event ?: event,
        selection = u.selection ?: selection,
        oddsDecimal = u.odds ?: oddsDecimal,
        stake = u.stake ?: stake,
        betType = u.betType ?: betType,
        side = u.side ?: side,
        currency = u.currency ?: currency,
        outcome = u.outcome ?: outcome,
        tournament = u.tournament ?: tournament,
        bookmaker = u.bookmaker ?: bookmaker,
        portal = u.portal ?: portal,
        tipster = u.tipster ?: tipster,
        notes = u.notes ?: notes,
        eachWay = u.eachWay ?: eachWay,
        placed = u.placed ?: placed,
        freeBet = u.freeBet ?: freeBet,
        cashOutAmount = u.cashOutAmount ?: cashOutAmount,
        closingOdds = u.closingOdds ?: closingOdds,
        eventAt = u.eventAt ?: eventAt,
    )
    return next.copy(profit = next.localProfit(), pendingSync = true)
}

private fun BetDto.localProfit(): Double = BetMath.settleProfit(
    stake = stake,
    decimalOdds = oddsDecimal,
    outcome = outcome,
    eachWay = eachWay,
    placeFraction = placeFraction,
    placed = placed,
    cashOutAmount = cashOutAmount,
    side = side,
    freeBet = freeBet,
)

/** The row shown for a bet recorded with no connection, before the server sees it. */
private fun BetCreateDto.toOptimisticBet(localId: String): BetDto {
    val decimalOdds = when {
        isMultiple && !legs.isNullOrEmpty() ->
            BetMath.combinedOdds(legs.map { it.decimalOdds() }) ?: 1.0
        oddsFormat == "fractional" && oddsDenominator != null && odds != null ->
            BetMath.fractionalToDecimal(odds, oddsDenominator)
        else -> odds ?: 1.0
    }
    val bet = BetDto(
        id = localId,
        tournament = tournament,
        event = event.orEmpty(),
        selection = selection.orEmpty(),
        sport = sport,
        betType = betType,
        side = side,
        isMultiple = isMultiple,
        legs = legs.orEmpty().mapIndexed { i, leg ->
            BetLegDto(
                legIndex = i,
                event = leg.event,
                selection = leg.selection,
                oddsDecimal = leg.decimalOdds(),
            )
        },
        placedAt = placedAt ?: OffsetDateTime.now().format(DateTimeFormatter.ISO_OFFSET_DATE_TIME),
        eventAt = eventAt,
        oddsDecimal = decimalOdds,
        oddsFormat = oddsFormat,
        stake = stake,
        currency = currency,
        eachWay = eachWay,
        placed = placed,
        freeBet = freeBet,
        outcome = outcome,
        cashOutAmount = cashOutAmount,
        bookmaker = bookmaker,
        portal = portal,
        tipster = tipster,
        notes = notes,
        closingOdds = closingOdds,
        pendingSync = true,
    )
    return bet.copy(profit = bet.localProfit())
}

private fun com.mybetrecord.android.data.remote.BetLegCreateDto.decimalOdds(): Double =
    if (oddsFormat == "fractional" && oddsDenominator != null) {
        BetMath.fractionalToDecimal(odds, oddsDenominator)
    } else {
        odds
    }

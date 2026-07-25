package com.mybetrecord.android.data.repository

import com.mybetrecord.android.data.local.BetDao
import com.mybetrecord.android.data.local.BetEntity
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.remote.BetsApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BetsRepository @Inject constructor(
    private val api: BetsApi,
    private val betDao: BetDao,
    private val json: Json,
) {
    fun observeCachedBets(): Flow<List<BetDto>> =
        betDao.observeBets().map { rows -> rows.mapNotNull { decode(it) } }

    suspend fun refreshBets(): List<BetDto> {
        val remote = api.listBets()
        betDao.upsertAll(remote.map { encode(it) })
        return remote
    }

    suspend fun getBet(id: String): BetDto {
        return try {
            val remote = api.getBet(id)
            betDao.upsert(encode(remote))
            remote
        } catch (e: Exception) {
            betDao.getById(id)?.let { decode(it) } ?: throw e
        }
    }

    suspend fun createBet(body: BetCreateDto): BetDto {
        val created = api.createBet(body)
        betDao.upsert(encode(created))
        return created
    }

    suspend fun updateBet(id: String, body: BetUpdateDto): BetDto {
        val updated = api.updateBet(id, body)
        betDao.upsert(encode(updated))
        return updated
    }

    suspend fun deleteBet(id: String) {
        val response = api.deleteBet(id)
        if (!response.isSuccessful && response.code() != 204) {
            throw IllegalStateException("Delete failed (${response.code()})")
        }
        betDao.delete(id)
    }

    private fun encode(bet: BetDto): BetEntity = BetEntity(
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
    )

    private fun decode(entity: BetEntity): BetDto? = try {
        json.decodeFromString(BetDto.serializer(), entity.payloadJson)
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
        )
    }
}

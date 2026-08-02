package com.mybetrecord.android.data.local

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "bets_cache")
data class BetEntity(
    @PrimaryKey val id: String,
    val event: String,
    val selection: String,
    val sport: String,
    val betType: String,
    val oddsDecimal: Double,
    val stake: Double,
    val currency: String,
    val outcome: String,
    val profit: Double,
    val placedAt: String,
    val bookmaker: String?,
    val payloadJson: String,
    /** True while a local change to this bet is still queued for the server. */
    val pendingSync: Boolean = false,
)

@Dao
interface BetDao {
    @Query("SELECT * FROM bets_cache ORDER BY placedAt DESC")
    fun observeBets(): Flow<List<BetEntity>>

    @Query("SELECT * FROM bets_cache WHERE id = :id LIMIT 1")
    suspend fun getById(id: String): BetEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(items: List<BetEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: BetEntity)

    @Query("DELETE FROM bets_cache WHERE id = :id")
    suspend fun delete(id: String)

    /**
     * Replaces the server's view of the ledger while leaving locally queued
     * rows alone, so a refresh never discards work that has not synced yet.
     */
    @Query("DELETE FROM bets_cache WHERE pendingSync = 0")
    suspend fun clearSynced()

    @Query("DELETE FROM bets_cache")
    suspend fun clear()
}

/** The kind of change queued against the server while offline. */
object PendingOpType {
    const val CREATE = "create"
    const val UPDATE = "update"
    const val DELETE = "delete"
}

/**
 * One queued write. Ops replay in insertion order so a create always reaches
 * the server before the edits that follow it.
 */
@Entity(tableName = "pending_ops")
data class PendingOpEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    /** Local id ("local-…") for offline creates, otherwise the server id. */
    val betId: String,
    val type: String,
    val payloadJson: String,
    val createdAt: Long = System.currentTimeMillis(),
    /** Set when the server rejected the change outright; excluded from retries. */
    val failed: Boolean = false,
    val lastError: String? = null,
)

@Dao
interface PendingOpDao {
    @Query("SELECT * FROM pending_ops WHERE failed = 0 ORDER BY id ASC")
    suspend fun pending(): List<PendingOpEntity>

    @Query("SELECT COUNT(*) FROM pending_ops WHERE failed = 0")
    fun observePendingCount(): Flow<Int>

    @Query("SELECT COUNT(*) FROM pending_ops WHERE failed = 1")
    fun observeFailedCount(): Flow<Int>

    @Query("SELECT * FROM pending_ops WHERE betId = :betId AND type = :type AND failed = 0 LIMIT 1")
    suspend fun findFor(betId: String, type: String): PendingOpEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(op: PendingOpEntity): Long

    @Query("DELETE FROM pending_ops WHERE id = :id")
    suspend fun delete(id: Long)

    @Query("DELETE FROM pending_ops WHERE betId = :betId")
    suspend fun deleteForBet(betId: String)

    @Query("UPDATE pending_ops SET failed = 1, lastError = :error WHERE id = :id")
    suspend fun markFailed(id: Long, error: String?)

    @Query("DELETE FROM pending_ops")
    suspend fun clear()
}

/**
 * Last good response for a reports query, so the page still renders in a dead
 * spot. Keyed by endpoint + filters; [fetchedAt] drives the "as of" note.
 */
@Entity(tableName = "report_cache")
data class ReportCacheEntity(
    @PrimaryKey val key: String,
    val payloadJson: String,
    val fetchedAt: Long = System.currentTimeMillis(),
)

@Dao
interface ReportCacheDao {
    @Query("SELECT * FROM report_cache WHERE `key` = :key LIMIT 1")
    suspend fun get(key: String): ReportCacheEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entry: ReportCacheEntity)

    @Query("DELETE FROM report_cache")
    suspend fun clear()
}

@Database(
    entities = [BetEntity::class, PendingOpEntity::class, ReportCacheEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun betDao(): BetDao
    abstract fun pendingOpDao(): PendingOpDao
    abstract fun reportCacheDao(): ReportCacheDao
}

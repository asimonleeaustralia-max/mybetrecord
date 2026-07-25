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

    @Query("DELETE FROM bets_cache")
    suspend fun clear()
}

@Database(entities = [BetEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun betDao(): BetDao
}

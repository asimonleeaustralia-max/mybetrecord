package com.mybetrecord.android.di

import android.content.Context
import androidx.room.Room
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.mybetrecord.android.BuildConfig
import com.mybetrecord.android.data.local.AppDatabase
import com.mybetrecord.android.data.local.BetDao
import com.mybetrecord.android.data.local.PendingOpDao
import com.mybetrecord.android.data.local.ReportCacheDao
import com.mybetrecord.android.data.remote.AuthApi
import com.mybetrecord.android.data.remote.AuthInterceptor
import com.mybetrecord.android.data.remote.BetsApi
import com.mybetrecord.android.data.remote.ReportsApi
import com.mybetrecord.android.data.remote.TokenAuthenticator
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit
import javax.inject.Named
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
    }

    @Provides
    @Singleton
    @Named("baseUrl")
    fun provideBaseUrl(): String {
        val raw = BuildConfig.API_BASE_URL
        return if (raw.endsWith("/")) raw else "$raw/"
    }

    @Provides
    @Singleton
    fun provideOkHttp(
        authInterceptor: AuthInterceptor,
        authenticator: TokenAuthenticator,
    ): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BASIC
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }
        return OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(authInterceptor)
            .authenticator(authenticator)
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(
        client: OkHttpClient,
        json: Json,
        @Named("baseUrl") baseUrl: String,
    ): Retrofit {
        val contentType = "application/json".toMediaType()
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
    }

    @Provides
    @Singleton
    fun provideAuthApi(retrofit: Retrofit): AuthApi = retrofit.create(AuthApi::class.java)

    @Provides
    @Singleton
    fun provideBetsApi(retrofit: Retrofit): BetsApi = retrofit.create(BetsApi::class.java)

    @Provides
    @Singleton
    fun provideReportsApi(retrofit: Retrofit): ReportsApi = retrofit.create(ReportsApi::class.java)

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "mybetrecord.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    @Singleton
    fun provideBetDao(db: AppDatabase): BetDao = db.betDao()

    @Provides
    @Singleton
    fun providePendingOpDao(db: AppDatabase): PendingOpDao = db.pendingOpDao()

    @Provides
    @Singleton
    fun provideReportCacheDao(db: AppDatabase): ReportCacheDao = db.reportCacheDao()
}

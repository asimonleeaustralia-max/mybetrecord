package com.mybetrecord.android

import android.app.Application
import com.mybetrecord.android.data.local.AppPreferences
import com.mybetrecord.android.data.sync.SyncManager
import com.mybetrecord.android.i18n.I18n
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltAndroidApp
class MyBetRecordApp : Application() {
    @Inject lateinit var appPreferences: AppPreferences
    @Inject lateinit var syncManager: SyncManager

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        I18n.init(this, appPreferences.getLocaleBlocking())

        // Replay offline writes and keep report data on device. Watching starts
        // unconditionally so signing in later still gets a sync; each run bails
        // out early when there is no session.
        syncManager.start(appScope)
        appScope.launch { syncManager.syncNow() }
    }
}

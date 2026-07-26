package com.mybetrecord.android

import android.app.Application
import com.mybetrecord.android.data.local.AppPreferences
import com.mybetrecord.android.i18n.I18n
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class MyBetRecordApp : Application() {
    @Inject lateinit var appPreferences: AppPreferences

    override fun onCreate() {
        super.onCreate()
        I18n.init(this, appPreferences.getLocaleBlocking())
    }
}

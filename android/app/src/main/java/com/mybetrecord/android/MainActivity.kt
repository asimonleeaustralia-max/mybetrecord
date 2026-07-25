package com.mybetrecord.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.mybetrecord.android.ui.navigation.MyBetRecordNavHost
import com.mybetrecord.android.ui.theme.MyBetRecordTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyBetRecordTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    MyBetRecordNavHost()
                }
            }
        }
    }
}

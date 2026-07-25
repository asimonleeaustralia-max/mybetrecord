package com.mybetrecord.android.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val GreenPrimary = Color(0xFF0B3D2E)
private val GreenSecondary = Color(0xFF1F6F54)
private val SurfaceLight = Color(0xFFF4F7F5)
private val SurfaceDark = Color(0xFF0E1A16)

private val LightColors = lightColorScheme(
    primary = GreenPrimary,
    secondary = GreenSecondary,
    background = SurfaceLight,
    surface = Color.White,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = Color(0xFF102018),
    onSurface = Color(0xFF102018),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF7BC9A8),
    secondary = Color(0xFF4FA884),
    background = SurfaceDark,
    surface = Color(0xFF15241E),
    onPrimary = Color(0xFF042018),
    onSecondary = Color(0xFF042018),
    onBackground = Color(0xFFE8F2ED),
    onSurface = Color(0xFFE8F2ED),
)

@Composable
fun MyBetRecordTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}

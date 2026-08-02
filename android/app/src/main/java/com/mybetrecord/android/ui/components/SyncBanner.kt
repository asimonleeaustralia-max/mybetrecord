package com.mybetrecord.android.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.CloudQueue
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.i18n.tr

/**
 * Slim strip under the app's content telling the user their changes are safe
 * but not yet on the server. Stays out of the way: it only appears when the
 * device is offline or something is actually queued.
 */
@Composable
fun SyncBanner(
    modifier: Modifier = Modifier,
    viewModel: SyncStatusViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    val banner: BannerSpec? = when {
        state.failedCount > 0 -> BannerSpec(
            icon = Icons.Default.ErrorOutline,
            text = tr("android.syncFailed", mapOf("count" to state.failedCount.toString())),
            container = MaterialTheme.colorScheme.errorContainer,
            content = MaterialTheme.colorScheme.onErrorContainer,
        )
        state.pendingCount > 0 -> BannerSpec(
            icon = Icons.Default.CloudQueue,
            text = tr("android.syncPending", mapOf("count" to state.pendingCount.toString())),
            container = MaterialTheme.colorScheme.tertiaryContainer,
            content = MaterialTheme.colorScheme.onTertiaryContainer,
        )
        !state.online -> BannerSpec(
            icon = Icons.Default.CloudOff,
            text = tr("android.offline"),
            container = MaterialTheme.colorScheme.surfaceVariant,
            content = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        else -> null
    }

    AnimatedVisibility(visible = banner != null, modifier = modifier) {
        banner?.let {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(it.container)
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Icon(it.icon, contentDescription = null, tint = it.content, modifier = Modifier.size(16.dp))
                Text(it.text, style = MaterialTheme.typography.labelMedium, color = it.content)
            }
        }
    }
}

private data class BannerSpec(
    val icon: ImageVector,
    val text: String,
    val container: Color,
    val content: Color,
)

package com.mybetrecord.android.ui.components

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.local.NetworkMonitor
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.data.sync.SyncManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class SyncStatus(
    val online: Boolean = true,
    val pendingCount: Int = 0,
    val failedCount: Int = 0,
    val syncing: Boolean = false,
)

@HiltViewModel
class SyncStatusViewModel @Inject constructor(
    betsRepository: BetsRepository,
    networkMonitor: NetworkMonitor,
    syncManager: SyncManager,
) : ViewModel() {
    val state: StateFlow<SyncStatus> = combine(
        networkMonitor.isOnline,
        betsRepository.observePendingCount(),
        betsRepository.observeFailedCount(),
        syncManager.syncing,
    ) { online, pending, failed, syncing ->
        SyncStatus(online = online, pendingCount = pending, failedCount = failed, syncing = syncing)
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = SyncStatus(online = networkMonitor.currentlyOnline()),
    )
}

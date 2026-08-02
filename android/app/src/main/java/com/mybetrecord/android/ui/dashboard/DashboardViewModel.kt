package com.mybetrecord.android.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.repository.ReportsRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val summary: ReportSummaryDto? = null,
    /** These figures came from the on-device copy rather than the server. */
    val fromCache: Boolean = false,
    val fetchedAt: Long? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val reportsRepository: ReportsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                val summary = reportsRepository.summary()
                _state.update {
                    it.copy(
                        loading = false,
                        summary = summary.value,
                        fromCache = summary.fromCache,
                        fetchedAt = summary.fetchedAt,
                        error = null,
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }
}

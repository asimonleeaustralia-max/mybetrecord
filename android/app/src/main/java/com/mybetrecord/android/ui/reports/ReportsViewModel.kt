package com.mybetrecord.android.ui.reports

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

data class ReportsUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val summary: ReportSummaryDto? = null,
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val reportsRepository: ReportsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                _state.update { it.copy(loading = false, summary = reportsRepository.summary()) }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }
}

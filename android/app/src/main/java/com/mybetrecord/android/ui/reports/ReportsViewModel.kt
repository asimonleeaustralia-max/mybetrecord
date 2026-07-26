package com.mybetrecord.android.ui.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.EquityPointDto
import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.repository.ReportsRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

data class MonthlyProfit(val month: String, val profit: Double)

data class ReportsUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val summary: ReportSummaryDto? = null,
    val equity: List<EquityPointDto> = emptyList(),
    val monthly: List<MonthlyProfit> = emptyList(),
    val exporting: Boolean = false,
    /** Set when an export finished downloading; the screen consumes it to share. */
    val exportFile: File? = null,
    val exportMime: String? = null,
)

private val EXPORT_MIME = mapOf(
    "csv" to "text/csv",
    "json" to "application/json",
    "xlsx" to "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
                val summary = reportsRepository.summary()
                val equity = reportsRepository.equityCurve()
                _state.update {
                    it.copy(
                        loading = false,
                        summary = summary,
                        equity = equity,
                        monthly = monthlyFromEquity(equity),
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    /** Same aggregation the web app uses for its "Profit by month" bar chart. */
    private fun monthlyFromEquity(points: List<EquityPointDto>): List<MonthlyProfit> {
        val byMonth = linkedMapOf<String, Double>()
        for (p in points) {
            val key = p.date.take(7) // YYYY-MM
            byMonth[key] = (byMonth[key] ?: 0.0) + p.profit
        }
        return byMonth.entries.sortedBy { it.key }.map { MonthlyProfit(it.key, it.value) }
    }

    fun export(kind: String) {
        viewModelScope.launch {
            _state.update { it.copy(exporting = true, error = null) }
            try {
                val file = reportsRepository.downloadExport(kind)
                _state.update {
                    it.copy(exporting = false, exportFile = file, exportMime = EXPORT_MIME.getValue(kind))
                }
            } catch (t: Throwable) {
                _state.update { it.copy(exporting = false, error = t.toUserMessage()) }
            }
        }
    }

    fun consumeExport() {
        _state.update { it.copy(exportFile = null, exportMime = null) }
    }
}

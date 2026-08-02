package com.mybetrecord.android.ui.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.BreakdownRowDto
import com.mybetrecord.android.data.remote.EquityPointDto
import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.repository.BetFilterOptions
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.data.repository.ReportFilters
import com.mybetrecord.android.data.repository.ReportsRepository
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException
import javax.inject.Inject

data class MonthlyProfit(val month: String, val profit: Double)

/** The four groupings the web app's "By dimension" panel offers. */
val BREAKDOWN_DIMENSIONS = listOf(
    "sport" to "reports.dimSport",
    "tipster" to "reports.dimTipster",
    "bet_type" to "reports.dimBetType",
    "bookmaker" to "reports.dimBookmaker",
)

data class ReportsUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val summary: ReportSummaryDto? = null,
    val equity: List<EquityPointDto> = emptyList(),
    val monthly: List<MonthlyProfit> = emptyList(),
    val breakdown: List<BreakdownRowDto> = emptyList(),
    val dimension: String = "sport",
    val filters: ReportFilters = ReportFilters(),
    val filterOptions: BetFilterOptions = BetFilterOptions(),
    /** True when these figures came from the on-device copy, not the server. */
    val fromCache: Boolean = false,
    /** When the server last answered for this view, for the "as of" note. */
    val fetchedAt: Long? = null,
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val reportsRepository: ReportsRepository,
    private val betsRepository: BetsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val options = betsRepository.filterOptions()
            _state.update { s ->
                s.copy(
                    filterOptions = options,
                    // The web page pre-selects the first currency so a mixed-currency
                    // ledger never sums into a meaningless total.
                    filters = if (s.filters.currency.isBlank() && options.currencies.isNotEmpty()) {
                        s.filters.copy(currency = options.currencies.first())
                    } else {
                        s.filters
                    },
                )
            }
            refresh()
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val filters = _state.value.filters
            val dimension = _state.value.dimension
            try {
                // The web page fires summary/equity/breakdown together; so do we.
                val (summary, equity, breakdown) = coroutineScope {
                    val summary = async { reportsRepository.summary(filters) }
                    val equity = async { reportsRepository.equityCurve(filters) }
                    val breakdown = async { reportsRepository.breakdown(dimension, filters) }
                    Triple(summary.await(), equity.await(), breakdown.await())
                }
                _state.update {
                    it.copy(
                        loading = false,
                        summary = summary.value,
                        equity = equity.value,
                        monthly = monthlyFromEquity(equity.value),
                        breakdown = breakdown.value,
                        fromCache = summary.fromCache,
                        fetchedAt = summary.fetchedAt,
                        error = null,
                    )
                }
            } catch (t: IOException) {
                // Offline with nothing cached for this view yet.
                _state.update {
                    it.copy(loading = false, error = tr("android.offlineNoReport"))
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    fun updateFilters(transform: (ReportFilters) -> ReportFilters) {
        _state.update { it.copy(filters = transform(it.filters)) }
        refresh()
    }

    fun clearFilters() {
        _state.update { it.copy(filters = ReportFilters()) }
        refresh()
    }

    /** Only the breakdown depends on the dimension, so reload just that panel. */
    fun selectDimension(dimension: String) {
        if (dimension == _state.value.dimension) return
        _state.update { it.copy(dimension = dimension) }
        viewModelScope.launch {
            try {
                val rows = reportsRepository.breakdown(dimension, _state.value.filters)
                _state.update { it.copy(breakdown = rows.value, error = null) }
            } catch (t: Throwable) {
                // This grouping was never downloaded; the rest of the page stands.
                _state.update { it.copy(breakdown = emptyList(), error = t.toUserMessage()) }
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
}

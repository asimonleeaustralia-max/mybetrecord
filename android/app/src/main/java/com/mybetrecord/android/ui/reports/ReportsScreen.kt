package com.mybetrecord.android.ui.reports

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.formatMoney

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen(
    padding: PaddingValues,
    viewModel: ReportsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    PullToRefreshBox(
        isRefreshing = state.loading && state.summary != null,
        onRefresh = viewModel::refresh,
        modifier = Modifier.padding(padding),
    ) {
        when {
            state.loading && state.summary == null -> LoadingScreen()
            else -> Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text("Reports", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "Summary metrics from your recorded bets.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                state.error?.let { ErrorText(it) }
                val s = state.summary ?: return@Column
                ReportRow("Profit", formatMoney(s.profit, s.currency ?: s.baseCurrency))
                ReportRow("Turnover", formatMoney(s.turnover, s.currency ?: s.baseCurrency))
                ReportRow("ROI", "%.2f%%".format(s.roiPct))
                ReportRow("Yield", "%.2f%%".format(s.yieldPct))
                ReportRow("Strike rate", "%.2f%%".format(s.strikeRatePct))
                ReportRow("Wins / losses / voids", "${s.wins} / ${s.losses} / ${s.voids}")
                ReportRow("Settled bets", s.settledBets.toString())
                ReportRow("Total bets", s.totalBets.toString())
                s.roiVsBankrollPct?.let {
                    ReportRow("ROI vs bankroll", "%.2f%%".format(it))
                }
            }
        }
    }
}

@Composable
private fun ReportRow(label: String, value: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp)) {
            Text(label, style = MaterialTheme.typography.labelLarge)
            Text(value, style = MaterialTheme.typography.titleLarge)
        }
    }
}

package com.mybetrecord.android.ui.dashboard

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
fun DashboardScreen(
    padding: PaddingValues,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    PullToRefreshBox(
        isRefreshing = state.loading && state.summary != null,
        onRefresh = viewModel::refresh,
        modifier = Modifier.padding(padding),
    ) {
        when {
            state.loading && state.summary == null -> LoadingScreen()
            else -> {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("Dashboard", style = MaterialTheme.typography.headlineSmall)
                    Text(
                        "Personal ledger summary. For record-keeping only.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    state.error?.let { ErrorText(it) }
                    val s = state.summary
                    if (s != null) {
                        MetricCard("Profit", formatMoney(s.profit, s.currency ?: s.baseCurrency))
                        MetricCard("Turnover", formatMoney(s.turnover, s.currency ?: s.baseCurrency))
                        MetricCard("Yield", "%.2f%%".format(s.yieldPct))
                        MetricCard("Strike rate", "%.2f%%".format(s.strikeRatePct))
                        MetricCard("Settled bets", s.settledBets.toString())
                        MetricCard("Total bets", s.totalBets.toString())
                        s.bankroll?.let {
                            MetricCard("Bankroll", formatMoney(it, s.baseCurrency))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricCard(label: String, value: String) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(label, style = MaterialTheme.typography.labelLarge)
            Text(value, style = MaterialTheme.typography.headlineSmall)
        }
    }
}

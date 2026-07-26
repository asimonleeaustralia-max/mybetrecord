package com.mybetrecord.android.ui.reports

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.formatMoney
import com.mybetrecord.android.util.shareFile

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen(
    padding: PaddingValues,
    viewModel: ReportsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    // Hand a finished export to the system share sheet, once.
    LaunchedEffect(state.exportFile) {
        val file = state.exportFile
        val mime = state.exportMime
        if (file != null && mime != null) {
            context.shareFile(file, mime)
            viewModel.consumeExport()
        }
    }

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
                Text(tr("reports.title"), style = MaterialTheme.typography.headlineSmall)
                Text(tr("android.summarySub"), style = MaterialTheme.typography.bodyMedium)
                state.error?.let { ErrorText(it) }
                val s = state.summary ?: return@Column
                val ccy = s.currency ?: s.baseCurrency

                ReportRow(tr("reports.profitLoss"), formatMoney(s.profit, ccy))
                ReportRow(tr("android.turnover"), formatMoney(s.turnover, ccy))
                ReportRow(tr("reports.roi"), "%.2f%%".format(s.roiPct))
                ReportRow(tr("reports.yield"), "%.2f%%".format(s.yieldPct))
                ReportRow(tr("reports.strikeRate"), "%.2f%%".format(s.strikeRatePct))
                ReportRow(
                    tr("reports.wlv", mapOf("wins" to s.wins.toString(), "losses" to s.losses.toString(), "voids" to s.voids.toString())),
                    "${s.settledBets} / ${s.totalBets}",
                )
                s.roiVsBankrollPct?.let {
                    ReportRow(tr("reports.ofBankroll", mapOf("pct" to "%.2f%%".format(it))), formatMoney(s.bankroll ?: 0.0, s.baseCurrency))
                }

                if (state.equity.size >= 2) {
                    Text(tr("reports.equityCurve"), style = MaterialTheme.typography.titleMedium)
                    Text(tr("reports.equitySub"), style = MaterialTheme.typography.bodySmall)
                    Card(Modifier.fillMaxWidth()) {
                        EquityCurveChart(
                            values = state.equity.map { it.cumulative },
                            modifier = Modifier.padding(16.dp),
                        )
                    }
                }

                if (state.monthly.isNotEmpty()) {
                    Text(tr("reports.profitByMonth"), style = MaterialTheme.typography.titleMedium)
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            MonthlyBarChart(values = state.monthly.map { it.profit })
                            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                                Text(state.monthly.first().month, style = MaterialTheme.typography.labelSmall)
                                if (state.monthly.size > 1) {
                                    Text(state.monthly.last().month, style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }

                Text(tr("android.exportShare"), style = MaterialTheme.typography.titleMedium)
                if (state.exporting) {
                    Text(tr("android.exporting"), style = MaterialTheme.typography.bodySmall)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { viewModel.export("csv") }, enabled = !state.exporting) {
                        Text(tr("reports.exportCsv"))
                    }
                    OutlinedButton(onClick = { viewModel.export("xlsx") }, enabled = !state.exporting) {
                        Text(tr("reports.exportXlsx"))
                    }
                    OutlinedButton(onClick = { viewModel.export("json") }, enabled = !state.exporting) {
                        Text(tr("reports.exportJson"))
                    }
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

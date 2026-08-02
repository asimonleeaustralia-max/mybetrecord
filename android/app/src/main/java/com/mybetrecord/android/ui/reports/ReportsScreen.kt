package com.mybetrecord.android.ui.reports

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.data.remote.BreakdownRowDto
import com.mybetrecord.android.data.repository.BetFilterOptions
import com.mybetrecord.android.data.repository.ReportFilters
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.ChoiceRow
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.formatMoney
import com.mybetrecord.android.util.formatPct
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

private val ProfitGreen = Color(0xFF157A52)
private val LossRed = Color(0xFFBD3A2B)

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
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(tr("reports.title"), style = MaterialTheme.typography.headlineSmall)
                if (state.fromCache) {
                    OfflineDataNote(state.fetchedAt)
                }
                state.error?.let { ErrorText(it) }

                FiltersPanel(
                    filters = state.filters,
                    options = state.filterOptions,
                    onChange = viewModel::updateFilters,
                    onClear = viewModel::clearFilters,
                )

                val s = state.summary ?: return@Column
                MetricCards(state)

                Panel(
                    title = tr("reports.equityCurve"),
                    subtitle = tr("reports.equitySub"),
                ) {
                    if (state.equity.size >= 2) {
                        EquityCurveChart(
                            labels = state.equity.map { shortDate(it.date) },
                            values = state.equity.map { it.cumulative },
                            formatValue = { formatMoney(it, s.currency ?: s.baseCurrency, signed = true) },
                        )
                    } else {
                        EmptyPanelText(tr("reports.noData"))
                    }
                }

                Panel(title = tr("reports.byDimension")) {
                    val dimensionLabel = tr(
                        BREAKDOWN_DIMENSIONS.first { it.first == state.dimension }.second,
                    )
                    ChoiceRow(
                        label = tr("reports.byDimension"),
                        options = BREAKDOWN_DIMENSIONS.map { (value, key) -> value to tr(key) },
                        selected = state.dimension,
                        onSelected = viewModel::selectDimension,
                    )
                    if (state.breakdown.isEmpty()) {
                        EmptyPanelText(tr("reports.noSettled"))
                    } else {
                        BreakdownTable(rows = state.breakdown, dimensionLabel = dimensionLabel)
                    }
                }

                Panel(title = tr("reports.profitByMonth")) {
                    if (state.monthly.isEmpty()) {
                        EmptyPanelText(tr("reports.noData"))
                    } else {
                        MonthlyBarChart(
                            labels = state.monthly.map { it.month },
                            values = state.monthly.map { it.profit },
                            formatValue = { formatMoney(it, s.currency ?: s.baseCurrency, signed = true) },
                        )
                    }
                }
            }
        }
    }
}

/** Tells the user these figures are the last downloaded copy, and how old it is. */
@Composable
private fun OfflineDataNote(fetchedAt: Long?) {
    val stamp = remember(fetchedAt) {
        fetchedAt?.let {
            Instant.ofEpochMilli(it).atZone(ZoneId.systemDefault()).format(OFFLINE_STAMP)
        }.orEmpty()
    }
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Row(
            Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Icon(
                Icons.Default.CloudOff,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                tr("android.offlineReport", mapOf("time" to stamp)),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** Card wrapper matching the web's .panel: a heading, optional sub, then content. */
@Composable
private fun Panel(
    title: String,
    subtitle: String? = null,
    content: @Composable () -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Column {
                Text(title, style = MaterialTheme.typography.titleMedium)
                subtitle?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            content()
        }
    }
}

@Composable
private fun EmptyPanelText(message: String) {
    Text(
        message,
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

/**
 * The five headline cards from the web reports page, laid out two per row.
 * Labels, values and the sub-line all mirror loadSummary() in the web app.
 */
@Composable
private fun MetricCards(state: ReportsUiState) {
    val s = state.summary ?: return
    val ccy = s.currency ?: s.baseCurrency
    val currencyNote = s.currency
        ?.let { tr("reports.currencyOnly", mapOf("currency" to it)) }
        ?: tr("reports.allCurrenciesNote")

    val cards = listOf(
        Metric(
            label = tr("reports.profitLoss"),
            value = formatMoney(s.profit, ccy, signed = true),
            sub = tr("reports.settled", mapOf("count" to s.settledBets.toString(), "note" to currencyNote)),
            tone = s.profit,
        ),
        Metric(
            label = tr("reports.roi"),
            value = formatPct(s.roiPct),
            sub = s.roiVsBankrollPct
                ?.let { tr("reports.ofBankroll", mapOf("pct" to formatPct(it))) }
                ?: tr("reports.perUnitStaked"),
        ),
        Metric(
            label = tr("reports.yield"),
            value = formatPct(s.yieldPct),
            sub = tr("reports.turnover", mapOf("amount" to formatMoney(s.turnover, ccy))),
        ),
        Metric(
            label = tr("reports.strikeRate"),
            value = formatPct(s.strikeRatePct),
            sub = tr(
                "reports.wlv",
                mapOf(
                    "wins" to s.wins.toString(),
                    "losses" to s.losses.toString(),
                    "voids" to s.voids.toString(),
                ),
            ),
        ),
        Metric(
            label = tr("reports.totalBets"),
            value = s.totalBets.toString(),
            sub = currencyNote,
        ),
    )

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        cards.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { metric ->
                    MetricCard(metric, Modifier.weight(1f))
                }
                // Keep the last odd card at half width rather than stretching it.
                if (row.size == 1) Box(Modifier.weight(1f))
            }
        }
    }
}

private data class Metric(
    val label: String,
    val value: String,
    val sub: String,
    /** When set, colours the value green/red the way the web's plClass does. */
    val tone: Double? = null,
)

@Composable
private fun MetricCard(metric: Metric, modifier: Modifier = Modifier) {
    Card(modifier) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                metric.label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                metric.value,
                style = MaterialTheme.typography.titleLarge,
                fontFamily = FontFamily.Monospace,
                color = plColor(metric.tone),
            )
            Text(
                metric.sub,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun plColor(value: Double?): Color = when {
    value == null || value == 0.0 -> MaterialTheme.colorScheme.onSurface
    value > 0 -> ProfitGreen
    else -> LossRed
}

/**
 * P/L here is bare, as in the web's breakdown table — the currency is already
 * named on the metric cards, and a prefix would wrap in the narrow column.
 */
@Composable
private fun BreakdownTable(rows: List<BreakdownRowDto>, dimensionLabel: String) {
    Column {
        Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
            HeaderCell(dimensionLabel, Modifier.weight(1f), leading = true)
            HeaderCell(tr("reports.bets"), Modifier.weight(0.6f))
            HeaderCell(tr("reports.strike"), Modifier.weight(0.7f))
            HeaderCell(tr("reports.yield"), Modifier.weight(0.7f))
            HeaderCell(tr("reports.pl"), Modifier.weight(0.9f))
        }
        HorizontalDivider()
        rows.forEach { row ->
            Row(
                Modifier.fillMaxWidth().padding(vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    row.key,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f),
                )
                NumberCell(row.settledBets.toString(), Modifier.weight(0.6f))
                NumberCell(formatPct(row.strikeRatePct), Modifier.weight(0.7f))
                NumberCell(formatPct(row.yieldPct), Modifier.weight(0.7f))
                NumberCell(
                    formatMoney(row.profit, null, signed = true),
                    Modifier.weight(0.9f),
                    color = plColor(row.profit),
                )
            }
            HorizontalDivider()
        }
    }
}

@Composable
private fun HeaderCell(text: String, modifier: Modifier = Modifier, leading: Boolean = false) {
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier,
        textAlign = if (leading) TextAlign.Start else TextAlign.End,
    )
}

@Composable
private fun NumberCell(
    text: String,
    modifier: Modifier = Modifier,
    color: Color = MaterialTheme.colorScheme.onSurface,
) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        fontFamily = FontFamily.Monospace,
        color = color,
        modifier = modifier,
        textAlign = TextAlign.End,
    )
}

/**
 * Collapsible version of the web page's filter bar. Every change reloads the
 * report, exactly like the web's change listeners.
 */
@Composable
private fun FiltersPanel(
    filters: ReportFilters,
    options: BetFilterOptions,
    onChange: ((ReportFilters) -> ReportFilters) -> Unit,
    onClear: () -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val activeCount = filters.toQuery().size

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    if (activeCount > 0) {
                        tr("android.filtersActive", mapOf("count" to activeCount.toString()))
                    } else {
                        tr("android.filters")
                    },
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.weight(1f),
                )
                if (activeCount > 0) {
                    TextButton(onClick = onClear) { Text(tr("android.clearFilters")) }
                }
                TextButton(onClick = { expanded = !expanded }) {
                    Icon(
                        if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = tr("android.filters"),
                    )
                }
            }

            AnimatedVisibility(expanded) {
                Column(
                    Modifier.padding(bottom = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    FilterChoice(
                        label = tr("bets.sport"),
                        anyLabel = tr("bets.all"),
                        values = options.sports,
                        selected = filters.sport,
                        onSelected = { v -> onChange { it.copy(sport = v) } },
                    )
                    FilterChoice(
                        label = tr("bets.type"),
                        anyLabel = tr("bets.all"),
                        values = options.betTypes,
                        selected = filters.betType,
                        onSelected = { v -> onChange { it.copy(betType = v) } },
                    )
                    FilterChoice(
                        label = tr("form.tipster"),
                        anyLabel = tr("bets.all"),
                        values = options.tipsters,
                        selected = filters.tipster,
                        onSelected = { v -> onChange { it.copy(tipster = v) } },
                    )
                    FilterChoice(
                        label = tr("form.currency"),
                        anyLabel = tr("reports.allCurrencies"),
                        values = options.currencies,
                        selected = filters.currency,
                        onSelected = { v -> onChange { it.copy(currency = v) } },
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        DateFilterField(
                            label = tr("bets.from"),
                            value = filters.dateFrom,
                            onChange = { v -> onChange { it.copy(dateFrom = v) } },
                            modifier = Modifier.weight(1f),
                        )
                        DateFilterField(
                            label = tr("bets.to"),
                            value = filters.dateTo,
                            onChange = { v -> onChange { it.copy(dateTo = v) } },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }
    }
}

/** Dropdown whose blank option means "all", as the web's empty <option> does. */
@Composable
private fun FilterChoice(
    label: String,
    anyLabel: String,
    values: List<String>,
    selected: String,
    onSelected: (String) -> Unit,
) {
    ChoiceRow(
        label = label,
        options = listOf("" to anyLabel) + values.map { it to it },
        selected = selected,
        onSelected = onSelected,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DateFilterField(
    label: String,
    value: String,
    onChange: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var showPicker by remember { mutableStateOf(false) }

    OutlinedButton(onClick = { showPicker = true }, modifier = modifier) {
        Text(
            if (value.isBlank()) "$label: ${tr("android.anyDate")}" else "$label: $value",
            style = MaterialTheme.typography.labelMedium,
        )
    }

    if (showPicker) {
        val pickerState = rememberDatePickerState(
            initialSelectedDateMillis = value.takeIf { it.isNotBlank() }?.let(::millisFromIsoDate),
        )
        DatePickerDialog(
            onDismissRequest = { showPicker = false },
            confirmButton = {
                TextButton(onClick = {
                    onChange(pickerState.selectedDateMillis?.let(::isoDateFromMillis).orEmpty())
                    showPicker = false
                }) { Text(tr("common.confirm")) }
            },
            dismissButton = {
                Row {
                    TextButton(onClick = {
                        onChange("")
                        showPicker = false
                    }) { Text(tr("android.anyDate")) }
                    TextButton(onClick = { showPicker = false }) { Text(tr("common.cancel")) }
                }
            },
        ) {
            DatePicker(state = pickerState)
        }
    }
}

private val ISO_DATE: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE
private val SHORT_DATE: DateTimeFormatter = DateTimeFormatter.ofPattern("dd MMM")
private val OFFLINE_STAMP: DateTimeFormatter = DateTimeFormatter.ofPattern("dd MMM, HH:mm")

/** The picker works in UTC millis; the API wants a plain yyyy-MM-dd. */
private fun isoDateFromMillis(millis: Long): String =
    Instant.ofEpochMilli(millis).atZone(ZoneOffset.UTC).toLocalDate().format(ISO_DATE)

private fun millisFromIsoDate(date: String): Long? = try {
    LocalDate.parse(date, ISO_DATE).atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()
} catch (_: Exception) {
    null
}

/** Equity points carry full ISO timestamps; the chart only needs "05 Mar". */
private fun shortDate(iso: String): String = try {
    LocalDate.parse(iso.take(10), ISO_DATE).format(SHORT_DATE)
} catch (_: Exception) {
    iso.take(10)
}

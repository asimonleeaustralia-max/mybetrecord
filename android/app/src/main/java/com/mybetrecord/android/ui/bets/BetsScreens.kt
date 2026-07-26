package com.mybetrecord.android.ui.bets

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ChoiceRow
import com.mybetrecord.android.ui.components.EmptyState
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.BetMath
import com.mybetrecord.android.util.formatMoney
import com.mybetrecord.android.util.shareLinkUrl
import com.mybetrecord.android.util.shareText

private val OUTCOMES = listOf("pending", "win", "loss", "void", "half_win", "half_loss", "placed")
private val PORTALS = listOf("" to "form.optional", "online" to "form.portalOnline", "phone" to "form.portalPhone", "in_shop" to "form.portalInShop")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BetsListScreen(
    padding: PaddingValues,
    onOpenBet: (String) -> Unit,
    onCreateBet: () -> Unit,
    viewModel: BetsListViewModel = hiltViewModel(),
) {
    val bets by viewModel.bets.collectAsStateWithLifecycle()
    val state by viewModel.state.collectAsStateWithLifecycle()
    var pendingDelete by remember { mutableStateOf<BetDto?>(null) }

    Scaffold(
        modifier = Modifier.padding(padding),
        floatingActionButton = {
            FloatingActionButton(onClick = onCreateBet) {
                Icon(Icons.Default.Add, contentDescription = tr("bets.recordBet"))
            }
        },
    ) { inner ->
        PullToRefreshBox(
            isRefreshing = state.refreshing,
            onRefresh = viewModel::refresh,
            modifier = Modifier
                .fillMaxSize()
                .padding(inner),
        ) {
            Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                Text(tr("bets.title"), style = MaterialTheme.typography.headlineSmall, modifier = Modifier.padding(vertical = 12.dp))
                state.error?.let { ErrorText(it) }
                if (bets.isEmpty() && !state.refreshing) {
                    EmptyState(tr("bets.empty"))
                } else {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(bets, key = { it.id }) { bet ->
                            BetRow(
                                bet = bet,
                                onClick = { onOpenBet(bet.id) },
                                onDelete = { pendingDelete = bet },
                            )
                        }
                    }
                }
            }
        }
    }

    pendingDelete?.let { bet ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text(tr("bets.deleteConfirm")) },
            text = { Text("${bet.event} / ${bet.selection}") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.delete(bet.id)
                    pendingDelete = null
                }) { Text(tr("common.confirm")) }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) { Text(tr("common.cancel")) }
            },
        )
    }
}

@Composable
private fun BetRow(bet: BetDto, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(bet.event, style = MaterialTheme.typography.titleMedium)
                val outcome = tr("outcomes.${bet.outcome}")
                val subtitle = buildString {
                    append(bet.selection)
                    append(" · ").append(bet.sport)
                    append(" · ").append(outcome)
                    if (bet.isMultiple) {
                        append(" · ").append(tr("bets.legsCount", mapOf("count" to bet.legs.size.toString())))
                    }
                    if (bet.freeBet) append(" · ").append(tr("form.freeBetBadge"))
                }
                Text(subtitle, style = MaterialTheme.typography.bodyMedium)
                val detail = buildString {
                    append("${tr("bets.odds")} ${bet.oddsDecimal}")
                    append(" · ${tr("form.stake")} ${formatMoney(bet.stake, bet.currency)}")
                    append(" · ${tr("bets.pl")} ${formatMoney(bet.profit, bet.currency)}")
                    bet.clvPct?.let { append(" · ${tr("bets.clv")} ${"%.2f".format(it)}%") }
                }
                Text(detail, style = MaterialTheme.typography.bodySmall)
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = tr("common.confirm"))
            }
        }
    }
}

@Composable
fun BetEditorScreen(
    onDone: () -> Unit,
    viewModel: BetEditorViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(state.saved, state.deleted) {
        if (state.saved || state.deleted) onDone()
    }

    if (state.loading) {
        LoadingScreen()
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(
            if (state.isEdit) tr("form.editTitle") else tr("form.recordTitle"),
            style = MaterialTheme.typography.headlineSmall,
        )
        state.error?.let { ErrorText(it) }

        AppTextField(state.sport, { viewModel.update { s -> s.copy(sport = it) } }, tr("form.sport"))
        AppTextField(state.betType, { viewModel.update { s -> s.copy(betType = it) } }, tr("form.betType"))

        // Single vs multiple (parlay). Multiples are created from legs; each-way,
        // free bets and fractional-vs-decimal apply per the backend's rules.
        if (!state.isEdit || state.isMultiple) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.isMultiple,
                    onCheckedChange = { checked ->
                        viewModel.update { s -> s.copy(isMultiple = checked, eachWay = false, freeBet = false) }
                    },
                    enabled = !state.isEdit,
                )
                Column {
                    Text(tr("form.multiple"))
                    Text(tr("form.multipleHint"), style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        // Odds format applies to the single bet's odds or to every leg.
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = state.oddsFormat == "decimal",
                onClick = { viewModel.update { s -> s.copy(oddsFormat = "decimal") } },
                label = { Text(tr("form.decimal")) },
            )
            FilterChip(
                selected = state.oddsFormat == "fractional",
                onClick = { viewModel.update { s -> s.copy(oddsFormat = "fractional") } },
                label = { Text(tr("form.fractional")) },
            )
        }

        if (state.isMultiple) {
            Text(tr("form.selections"), style = MaterialTheme.typography.titleMedium)
            Text(tr("form.legsHint"), style = MaterialTheme.typography.bodySmall)
            state.legs.forEachIndexed { index, leg ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                tr("form.legLabel", mapOf("n" to (index + 1).toString())),
                                style = MaterialTheme.typography.labelLarge,
                                modifier = Modifier.weight(1f),
                            )
                            if (state.legs.size > 2) {
                                IconButton(onClick = { viewModel.removeLeg(index) }) {
                                    Icon(Icons.Default.Delete, contentDescription = null)
                                }
                            }
                        }
                        AppTextField(leg.event, { viewModel.updateLeg(index) { l -> l.copy(event = it) } }, tr("form.event"))
                        AppTextField(leg.selection, { viewModel.updateLeg(index) { l -> l.copy(selection = it) } }, tr("form.selection"))
                        AppTextField(
                            leg.odds,
                            { viewModel.updateLeg(index) { l -> l.copy(odds = it) } },
                            if (state.oddsFormat == "fractional") "${tr("bets.odds")} (11/8)" else tr("form.decimalOdds"),
                            keyboardType = if (state.oddsFormat == "fractional") KeyboardType.Text else KeyboardType.Decimal,
                        )
                    }
                }
            }
            TextButton(onClick = viewModel::addLeg, enabled = state.legs.size < 10) {
                Text(tr("form.addSelection"))
            }
            viewModel.currentDecimalOdds()?.let { combined ->
                Text("${tr("form.combinedOdds")}: ${"%.2f".format(combined)}", style = MaterialTheme.typography.bodyMedium)
            }
        } else {
            AppTextField(state.event, { viewModel.update { s -> s.copy(event = it) } }, tr("form.event"))
            AppTextField(state.selection, { viewModel.update { s -> s.copy(selection = it) } }, tr("form.selection"))
            AppTextField(
                state.odds,
                { viewModel.update { s -> s.copy(odds = it) } },
                if (state.oddsFormat == "fractional") "${tr("bets.odds")} (11/8)" else tr("form.decimalOdds"),
                keyboardType = if (state.oddsFormat == "fractional") KeyboardType.Text else KeyboardType.Decimal,
            )
            if (state.oddsFormat == "fractional") {
                BetMath.parseFractional(state.odds)?.let { (n, d) ->
                    Text(
                        "${tr("form.effectiveOdds")}: ${"%.2f".format(BetMath.fractionalToDecimal(n, d))}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }

        AppTextField(state.eventAt, { viewModel.update { s -> s.copy(eventAt = it) } }, tr("form.eventAt") + " — " + tr("android.eventAtHint"))
        AppTextField(state.stake, { viewModel.update { s -> s.copy(stake = it) } }, tr("form.stake"), keyboardType = KeyboardType.Decimal)
        AppTextField(state.currency, { viewModel.update { s -> s.copy(currency = it) } }, tr("form.currency"))

        if (!state.isMultiple) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.eachWay,
                    onCheckedChange = { viewModel.update { s -> s.copy(eachWay = it) } },
                )
                Text(tr("form.eachWay"))
            }
            if (state.eachWay) {
                Text(tr("form.eachWayNote"), style = MaterialTheme.typography.bodySmall)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.freeBet,
                    onCheckedChange = { viewModel.update { s -> s.copy(freeBet = it) } },
                )
                Text(tr("form.freeBet"))
            }
            if (state.freeBet) {
                Text(tr("form.freeBetNote"), style = MaterialTheme.typography.bodySmall)
            }
        }

        Text(tr("form.settlement"), style = MaterialTheme.typography.titleMedium)
        ChoiceRow(
            label = tr("form.result"),
            options = OUTCOMES.map { it to tr("outcomes.$it") },
            selected = state.outcome,
            onSelected = { viewModel.update { s -> s.copy(outcome = it) } },
        )
        AppTextField(
            state.cashOut,
            { viewModel.update { s -> s.copy(cashOut = it) } },
            "${tr("form.cashOut")} (${tr("form.cashOutHint")})",
            keyboardType = KeyboardType.Decimal,
        )

        Text(tr("form.modelling"), style = MaterialTheme.typography.titleMedium)
        AppTextField(
            state.closingOdds,
            { viewModel.update { s -> s.copy(closingOdds = it) } },
            tr("android.closingOdds"),
            keyboardType = KeyboardType.Decimal,
        )
        state.clvPct?.let {
            Text("${tr("bets.clv")}: ${"%.2f".format(it)}%", style = MaterialTheme.typography.bodyMedium)
        }

        AppTextField(state.bookmaker, { viewModel.update { s -> s.copy(bookmaker = it) } }, tr("form.bookmaker"))
        ChoiceRow(
            label = tr("form.portal"),
            options = PORTALS.map { (value, key) -> value to tr(key) },
            selected = state.portal,
            onSelected = { viewModel.update { s -> s.copy(portal = it) } },
        )
        AppTextField(state.tipster, { viewModel.update { s -> s.copy(tipster = it) } }, tr("form.tipster"))
        AppTextField(state.notes, { viewModel.update { s -> s.copy(notes = it) } }, tr("form.notes"), singleLine = false)

        Button(
            onClick = viewModel::save,
            enabled = !state.saving,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (state.isEdit) tr("form.saveChanges") else tr("form.saveBet"))
        }

        if (state.isEdit) {
            Text(tr("share.shareSection"), style = MaterialTheme.typography.titleMedium)
            Text(tr("share.shareHint"), style = MaterialTheme.typography.bodySmall)
            val token = state.shareToken
            if (token == null) {
                OutlinedButton(
                    onClick = viewModel::createShareLink,
                    enabled = !state.sharing,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(tr("share.shareBet")) }
            } else {
                OutlinedButton(
                    onClick = { context.shareText(shareLinkUrl(token)) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(tr("share.copyLink")) }
                TextButton(onClick = viewModel::revokeShareLink, enabled = !state.sharing) {
                    Text(tr("share.revokeLink"), color = MaterialTheme.colorScheme.error)
                }
            }

            TextButton(onClick = viewModel::delete, enabled = !state.saving) {
                Text(tr("bets.deleteAria", mapOf("name" to state.selection)), color = MaterialTheme.colorScheme.error)
            }
        }
        TextButton(onClick = onDone) { Text(tr("form.cancel")) }
    }
}

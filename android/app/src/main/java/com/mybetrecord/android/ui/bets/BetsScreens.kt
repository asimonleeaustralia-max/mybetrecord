package com.mybetrecord.android.ui.bets

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.CloudQueue
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.graphics.Color
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

private val PORTALS =listOf("" to "form.optional", "online" to "form.portalOnline", "phone" to "form.portalPhone", "in_shop" to "form.portalInShop")

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
                                settling = bet.id in state.settling,
                                onClick = { onOpenBet(bet.id) },
                                onDelete = { pendingDelete = bet },
                                onOutcomeSelected = { viewModel.setOutcome(bet.id, it) },
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
private fun BetRow(
    bet: BetDto,
    settling: Boolean,
    onClick: () -> Unit,
    onDelete: () -> Unit,
    onOutcomeSelected: (String) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(bet.event, style = MaterialTheme.typography.titleMedium)
                    val subtitle = buildString {
                        append(bet.selection)
                        append(" · ").append(bet.sport)
                        if (bet.isMultiple) {
                            append(" · ").append(tr("bets.legsCount", mapOf("count" to bet.legs.size.toString())))
                        }
                        if (bet.freeBet) append(" · ").append(tr("form.freeBetBadge"))
                    }
                    Text(subtitle, style = MaterialTheme.typography.bodyMedium)
                    val detail = buildString {
                        append("${tr("bets.odds")} ${bet.oddsDecimal}")
                        append(" · ${tr("form.stake")} ${formatMoney(bet.stake, bet.currency)}")
                        append(" · ${tr("bets.pl")} ${formatMoney(bet.profit, bet.currency, signed = true)}")
                        bet.clvPct?.let { append(" · ${tr("bets.clv")} ${"%.2f".format(it)}%") }
                    }
                    Text(detail, style = MaterialTheme.typography.bodySmall)
                }
                IconButton(onClick = onDelete) {
                    Icon(
                        Icons.Default.Delete,
                        contentDescription = tr("bets.deleteAria", mapOf("name" to bet.selection)),
                    )
                }
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutcomePicker(bet = bet, settling = settling, onSelected = onOutcomeSelected)
                if (bet.pendingSync) {
                    PendingSyncBadge()
                }
            }
        }
    }
}

/**
 * Settles a bet without opening the editor — the mobile equivalent of the
 * result dropdown on each row of the web ledger.
 */
@Composable
private fun OutcomePicker(bet: BetDto, settling: Boolean, onSelected: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val current = displayOutcome(bet)

    Box {
        AssistChip(
            onClick = { expanded = true },
            enabled = !settling,
            label = { Text(if (settling) tr("android.savingResult") else tr("outcomes.$current")) },
            leadingIcon = {
                Box(
                    Modifier
                        .size(10.dp)
                        .background(outcomeColor(current), CircleShape),
                )
            },
            trailingIcon = {
                Icon(Icons.Default.ArrowDropDown, contentDescription = tr("android.setResult"))
            },
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            outcomeOptions(bet.eachWay).forEach { option ->
                DropdownMenuItem(
                    text = { Text(tr("outcomes.$option")) },
                    onClick = {
                        expanded = false
                        if (option != current) onSelected(option)
                    },
                )
            }
        }
    }
}

/** Marks a row whose latest change is still sitting in the outbox. */
@Composable
private fun PendingSyncBadge() {
    Row(
        modifier = Modifier
            .background(
                MaterialTheme.colorScheme.tertiaryContainer,
                MaterialTheme.shapes.small,
            )
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(
            Icons.Default.CloudQueue,
            contentDescription = null,
            modifier = Modifier.size(14.dp),
            tint = MaterialTheme.colorScheme.onTertiaryContainer,
        )
        Text(
            tr("android.pendingBadge"),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onTertiaryContainer,
        )
    }
}

/** Heading for one of the form's sections — the app's take on the web's <legend>. */
@Composable
private fun SectionHeader(title: String) {
    Text(
        title,
        style = MaterialTheme.typography.titleMedium,
        modifier = Modifier.padding(top = 8.dp),
    )
}

/** Same win/loss/void/pending tones the web ledger paints its result select with. */
@Composable
private fun outcomeColor(outcome: String): Color = when (outcome) {
    "win", "placed", "half_win" -> Color(0xFF157A52)
    "loss", "half_loss" -> Color(0xFFBD3A2B)
    "void" -> MaterialTheme.colorScheme.outline
    else -> MaterialTheme.colorScheme.secondary
}

@Composable
fun BetEditorScreen(
    onDone: () -> Unit,
    viewModel: BetEditorViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var confirmDelete by remember { mutableStateOf(false) }

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

        // Section order and grouping follow the web app's <fieldset>s so the two
        // clients read the same way.
        SectionHeader(tr("form.whatYouBacked"))

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

        AppTextField(state.sport, { viewModel.update { s -> s.copy(sport = it) } }, tr("form.sport"))
        AppTextField(state.betType, { viewModel.update { s -> s.copy(betType = it) } }, tr("form.betType"))
        AppTextField(state.bookmaker, { viewModel.update { s -> s.copy(bookmaker = it) } }, tr("form.bookmaker"))
        ChoiceRow(
            label = tr("form.portal"),
            options = PORTALS.map { (value, key) -> value to tr(key) },
            selected = state.portal,
            onSelected = { viewModel.update { s -> s.copy(portal = it) } },
        )

        // A multiple's event/selection live on its legs instead.
        if (!state.isMultiple) {
            AppTextField(state.event, { viewModel.update { s -> s.copy(event = it) } }, tr("form.event"))
            AppTextField(state.selection, { viewModel.update { s -> s.copy(selection = it) } }, tr("form.selection"))
        }
        AppTextField(state.eventAt, { viewModel.update { s -> s.copy(eventAt = it) } }, tr("form.eventAt") + " — " + tr("android.eventAtHint"))

        if (state.isMultiple) {
            SectionHeader(tr("form.selections"))
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
        }

        SectionHeader(tr("form.oddsStake"))

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

        if (!state.isMultiple) {
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

        AppTextField(state.stake, { viewModel.update { s -> s.copy(stake = it) } }, tr("form.stake"), keyboardType = KeyboardType.Decimal)
        AppTextField(state.currency, { viewModel.update { s -> s.copy(currency = it) } }, tr("form.currency"))

        if (!state.isMultiple) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.eachWay,
                    // Each-way swaps which results are valid, so drop one that no longer is.
                    onCheckedChange = { checked ->
                        viewModel.update { s ->
                            s.copy(
                                eachWay = checked,
                                outcome = s.outcome.takeIf { it in outcomeOptions(checked) } ?: "pending",
                            )
                        }
                    },
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

        SectionHeader(tr("form.settlement"))
        ChoiceRow(
            label = tr("form.result"),
            options = outcomeOptions(state.eachWay).map { it to tr("outcomes.$it") },
            selected = state.outcome,
            onSelected = { viewModel.update { s -> s.copy(outcome = it) } },
        )
        AppTextField(
            state.cashOut,
            { viewModel.update { s -> s.copy(cashOut = it) } },
            "${tr("form.cashOut")} (${tr("form.cashOutHint")})",
            keyboardType = KeyboardType.Decimal,
        )

        SectionHeader(tr("form.modelling"))
        AppTextField(
            state.closingOdds,
            { viewModel.update { s -> s.copy(closingOdds = it) } },
            tr("android.closingOdds"),
            keyboardType = KeyboardType.Decimal,
        )
        state.clvPct?.let {
            Text("${tr("bets.clv")}: ${"%.2f".format(it)}%", style = MaterialTheme.typography.bodyMedium)
        }

        SectionHeader(tr("form.notes"))
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
            SectionHeader(tr("share.shareSection"))
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

            OutlinedButton(
                onClick = { confirmDelete = true },
                enabled = !state.saving,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.error,
                ),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.error),
            ) {
                Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text(tr("android.deleteBet"))
            }
        }
        TextButton(onClick = onDone) { Text(tr("form.cancel")) }
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text(tr("bets.deleteConfirm")) },
            text = { Text("${state.event} / ${state.selection}") },
            confirmButton = {
                TextButton(onClick = {
                    confirmDelete = false
                    viewModel.delete()
                }) {
                    Text(tr("android.deleteBet"), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = false }) { Text(tr("common.cancel")) }
            },
        )
    }
}

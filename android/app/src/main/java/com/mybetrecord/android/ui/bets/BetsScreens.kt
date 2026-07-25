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
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.EmptyState
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.formatMoney

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
                Icon(Icons.Default.Add, contentDescription = "Add bet")
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
                Text("Bets", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.padding(vertical = 12.dp))
                state.error?.let { ErrorText(it) }
                if (bets.isEmpty() && !state.refreshing) {
                    EmptyState("No bets yet. Tap + to record one.")
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
            title = { Text("Delete bet?") },
            text = { Text("Delete ${bet.event} / ${bet.selection}? This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.delete(bet.id)
                    pendingDelete = null
                }) { Text("Delete") }
            },
            dismissButton = {
                TextButton(onClick = { pendingDelete = null }) { Text("Cancel") }
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
                Text("${bet.selection} · ${bet.sport} · ${bet.outcome}", style = MaterialTheme.typography.bodyMedium)
                Text(
                    "Odds ${bet.oddsDecimal} · Stake ${formatMoney(bet.stake, bet.currency)} · P/L ${formatMoney(bet.profit, bet.currency)}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = "Delete")
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
            if (state.isEdit) "Edit bet" else "New bet",
            style = MaterialTheme.typography.headlineSmall,
        )
        state.error?.let { ErrorText(it) }
        AppTextField(state.sport, { viewModel.update { s -> s.copy(sport = it) } }, "Sport")
        AppTextField(state.event, { viewModel.update { s -> s.copy(event = it) } }, "Event")
        AppTextField(state.selection, { viewModel.update { s -> s.copy(selection = it) } }, "Selection")
        AppTextField(state.odds, { viewModel.update { s -> s.copy(odds = it) } }, "Odds (decimal)")
        AppTextField(state.stake, { viewModel.update { s -> s.copy(stake = it) } }, "Stake")
        AppTextField(state.currency, { viewModel.update { s -> s.copy(currency = it) } }, "Currency")
        AppTextField(state.betType, { viewModel.update { s -> s.copy(betType = it) } }, "Bet type")
        AppTextField(state.outcome, { viewModel.update { s -> s.copy(outcome = it) } }, "Outcome")
        AppTextField(state.bookmaker, { viewModel.update { s -> s.copy(bookmaker = it) } }, "Bookmaker")
        AppTextField(state.notes, { viewModel.update { s -> s.copy(notes = it) } }, "Notes", singleLine = false)
        androidx.compose.material3.Button(
            onClick = viewModel::save,
            enabled = !state.saving,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (state.saving) "Saving…" else "Save")
        }
        if (state.isEdit) {
            TextButton(onClick = viewModel::delete, enabled = !state.saving) {
                Text("Delete bet", color = MaterialTheme.colorScheme.error)
            }
        }
        TextButton(onClick = onDone) { Text("Cancel") }
    }
}

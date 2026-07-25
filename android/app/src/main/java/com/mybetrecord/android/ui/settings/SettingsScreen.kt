package com.mybetrecord.android.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.R
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.openUrl

@Composable
fun SettingsScreen(
    padding: PaddingValues,
    onLoggedOut: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(state.loggedOut, state.accountDeleted) {
        if (state.loggedOut || state.accountDeleted) onLoggedOut()
    }

    if (state.loading && state.user == null) {
        LoadingScreen(modifier = Modifier.padding(padding))
        return
    }

    Column(
        modifier = Modifier
            .padding(padding)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Settings", style = MaterialTheme.typography.headlineSmall)
        Text(stringResource(R.string.disclaimer), style = MaterialTheme.typography.bodySmall)
        state.error?.let { ErrorText(it) }
        state.info?.let { Text(it, color = MaterialTheme.colorScheme.secondary) }

        state.user?.let { user ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(stringResource(R.string.plan_status), style = MaterialTheme.typography.titleMedium)
                    Text("Email: ${user.email}")
                    Text("Plan: ${user.plan.uppercase()}${if (user.isPro) " (Pro active)" else ""}")
                    user.subscriptionStatus?.let { Text("Subscription status: $it") }
                    user.subscriptionCurrentPeriodEnd?.let { Text("Current period end: $it") }
                    Text(
                        "Plan changes are managed on the website. This app does not sell subscriptions.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    )
                }
            }
        }

        AppTextField(state.displayName, { viewModel.update { s -> s.copy(displayName = it) } }, "Display name")
        AppTextField(state.baseCurrency, { viewModel.update { s -> s.copy(baseCurrency = it) } }, "Base currency")
        AppTextField(state.bankroll, { viewModel.update { s -> s.copy(bankroll = it) } }, "Bankroll")
        AppTextField(state.timezone, { viewModel.update { s -> s.copy(timezone = it) } }, "Timezone")
        AppTextField(
            state.defaultOddsFormat,
            { viewModel.update { s -> s.copy(defaultOddsFormat = it) } },
            "Default odds format",
        )

        Button(
            onClick = viewModel::save,
            enabled = !state.saving,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (state.saving) "Saving…" else "Save settings")
        }

        Text("Legal & help", style = MaterialTheme.typography.titleMedium)
        LinkButton(stringResource(R.string.privacy)) {
            context.openUrl(context.getString(R.string.url_privacy))
        }
        LinkButton(stringResource(R.string.terms)) {
            context.openUrl(context.getString(R.string.url_terms))
        }
        LinkButton(stringResource(R.string.responsible_gambling)) {
            context.openUrl(context.getString(R.string.url_responsible))
        }
        LinkButton(stringResource(R.string.delete_account_web)) {
            context.openUrl(context.getString(R.string.url_delete))
        }

        OutlinedButton(
            onClick = viewModel::logout,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.logout))
        }

        Button(
            onClick = { viewModel.update { it.copy(showDeleteDialog = true, error = null) } },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.delete_account))
        }
    }

    if (state.showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { viewModel.update { it.copy(showDeleteDialog = false) } },
            title = { Text("Delete account permanently?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("This permanently deletes your account and bet history. Type DELETE to confirm.")
                    AppTextField(
                        value = state.deletePassword,
                        onValueChange = { viewModel.update { s -> s.copy(deletePassword = it) } },
                        label = "Password",
                        isPassword = true,
                    )
                    AppTextField(
                        value = state.deleteConfirm,
                        onValueChange = { viewModel.update { s -> s.copy(deleteConfirm = it) } },
                        label = "Type DELETE",
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = viewModel::deleteAccount) { Text("Delete forever") }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.update { it.copy(showDeleteDialog = false) } }) {
                    Text("Cancel")
                }
            },
        )
    }
}

@Composable
private fun LinkButton(label: String, onClick: () -> Unit) {
    TextButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Text(label)
    }
}

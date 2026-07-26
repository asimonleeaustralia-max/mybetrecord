package com.mybetrecord.android.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.R
import com.mybetrecord.android.i18n.I18n
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ChoiceRow
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.LoadingScreen
import com.mybetrecord.android.util.openUrl
import com.mybetrecord.android.util.publicProfileUrl
import com.mybetrecord.android.util.shareText

private val ODDS_FORMATS = listOf(
    "decimal" to "settings.oddsDecimal",
    "american" to "settings.oddsAmerican",
    "fractional" to "settings.oddsFractional",
    "hong_kong" to "settings.oddsHongKong",
    "malaysian" to "settings.oddsMalaysian",
    "indonesian" to "settings.oddsIndonesian",
)

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
        Text(tr("settings.title"), style = MaterialTheme.typography.headlineSmall)
        Text(stringResource(R.string.disclaimer), style = MaterialTheme.typography.bodySmall)
        state.error?.let { ErrorText(it) }
        state.info?.let { Text(it, color = MaterialTheme.colorScheme.secondary) }

        state.user?.let { user ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(stringResource(R.string.plan_status), style = MaterialTheme.typography.titleMedium)
                    Text("${tr("settings.email")}: ${user.email}")
                    Text("${tr("plan.title")}: ${user.plan.uppercase()}${if (user.isPro) " (Pro)" else ""}")
                    user.subscriptionStatus?.let { Text(it) }
                    Text(
                        tr("android.planWebNote"),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    )
                }
            }
        }

        Text(tr("settings.preferences"), style = MaterialTheme.typography.titleMedium)
        ChoiceRow(
            label = tr("settings.language"),
            options = I18n.languages,
            selected = state.locale,
            onSelected = { viewModel.update { s -> s.copy(locale = it) } },
        )
        AppTextField(state.displayName, { viewModel.update { s -> s.copy(displayName = it) } }, tr("settings.publicNickname"))
        AppTextField(state.baseCurrency, { viewModel.update { s -> s.copy(baseCurrency = it) } }, tr("settings.defaultCurrency"))
        AppTextField(state.bankroll, { viewModel.update { s -> s.copy(bankroll = it) } }, tr("settings.bankroll") + " (" + tr("settings.bankrollHint") + ")")
        AppTextField(state.kellyMultiplier, { viewModel.update { s -> s.copy(kellyMultiplier = it) } }, tr("settings.kellyMultiplier") + " (" + tr("settings.kellyHint") + ")")
        AppTextField(state.timezone, { viewModel.update { s -> s.copy(timezone = it) } }, tr("settings.timezone"))
        ChoiceRow(
            label = tr("settings.defaultOdds"),
            options = ODDS_FORMATS.map { (value, key) -> value to tr(key) },
            selected = state.defaultOddsFormat,
            onSelected = { viewModel.update { s -> s.copy(defaultOddsFormat = it) } },
        )

        Text(tr("settings.publicBetsTitle"), style = MaterialTheme.typography.titleMedium)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(
                checked = state.publicBetsEnabled,
                onCheckedChange = { viewModel.update { s -> s.copy(publicBetsEnabled = it) } },
            )
            Text(
                tr("settings.publicBetsEnabled"),
                modifier = Modifier.padding(start = 8.dp),
            )
        }
        Text(tr("settings.publicBetsHint"), style = MaterialTheme.typography.bodySmall)
        if (state.publicBetsEnabled) {
            AppTextField(
                state.accountDescription,
                { viewModel.update { s -> s.copy(accountDescription = it) } },
                tr("settings.accountDescription"),
                singleLine = false,
            )
            state.user?.publicBetsToken?.let { token ->
                OutlinedButton(
                    onClick = { context.shareText(publicProfileUrl(token)) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(tr("android.shareProfile")) }
            }
        }

        Button(
            onClick = viewModel::save,
            enabled = !state.saving,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(tr("settings.save"))
        }

        Text(tr("android.legalHelp"), style = MaterialTheme.typography.titleMedium)
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
            Text(tr("nav.signOut"))
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
            title = { Text(stringResource(R.string.delete_account)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(tr("android.deleteAccountBody"))
                    AppTextField(
                        value = state.deletePassword,
                        onValueChange = { viewModel.update { s -> s.copy(deletePassword = it) } },
                        label = tr("auth.password"),
                        isPassword = true,
                    )
                    AppTextField(
                        value = state.deleteConfirm,
                        onValueChange = { viewModel.update { s -> s.copy(deleteConfirm = it) } },
                        label = tr("android.typeDelete"),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = viewModel::deleteAccount) { Text(tr("android.deleteForever")) }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.update { it.copy(showDeleteDialog = false) } }) {
                    Text(tr("common.cancel"))
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

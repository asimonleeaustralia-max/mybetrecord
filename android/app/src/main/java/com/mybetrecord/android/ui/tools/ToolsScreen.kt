package com.mybetrecord.android.ui.tools

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.util.BetMath
import com.mybetrecord.android.util.formatMoney

@Composable
fun ToolsScreen(
    padding: PaddingValues,
    viewModel: ToolsViewModel = hiltViewModel(),
) {
    val user by viewModel.user.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .padding(padding)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(tr("android.tools"), style = MaterialTheme.typography.headlineSmall)
        Text(tr("android.toolsSub"), style = MaterialTheme.typography.bodySmall)

        KellyCalculatorCard(
            defaultBankroll = user?.bankroll?.takeIf { it > 0 }?.toString().orEmpty(),
            defaultMultiplier = user?.kellyMultiplier?.toString() ?: "1.0",
            currency = user?.baseCurrency ?: "GBP",
        )
        LiabilityCalculatorCard(currency = user?.baseCurrency ?: "GBP")
    }
}

@Composable
private fun KellyCalculatorCard(
    defaultBankroll: String,
    defaultMultiplier: String,
    currency: String,
) {
    var odds by remember { mutableStateOf("") }
    var implied by remember { mutableStateOf("") }
    var bankroll by remember(defaultBankroll) { mutableStateOf(defaultBankroll) }
    var multiplier by remember(defaultMultiplier) { mutableStateOf(defaultMultiplier) }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(tr("android.kellyTitle"), style = MaterialTheme.typography.titleMedium)
            AppTextField(odds, { odds = it }, tr("android.kellyOdds"), keyboardType = KeyboardType.Decimal)
            AppTextField(implied, { implied = it }, tr("android.kellyImplied"), keyboardType = KeyboardType.Decimal)
            AppTextField(bankroll, { bankroll = it }, tr("settings.bankroll"), keyboardType = KeyboardType.Decimal)
            AppTextField(multiplier, { multiplier = it }, tr("settings.kellyMultiplier") + " (" + tr("settings.kellyHint") + ")", keyboardType = KeyboardType.Decimal)

            val o = odds.toDoubleOrNull()
            val i = implied.toDoubleOrNull()
            val b = bankroll.toDoubleOrNull()
            val m = multiplier.toDoubleOrNull() ?: 1.0
            if (o != null && i != null) {
                val edge = BetMath.edgePct(o, i)
                if (edge != null) {
                    Text(
                        "${tr("form.personalEdge")}: ${tr("form.edgeValue", mapOf("pct" to "%.2f".format(edge)))}",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                if (b != null && b > 0) {
                    val kelly = BetMath.kelly(o, i, b, m)
                    Text(
                        if (kelly != null && kelly.fraction > 0) {
                            tr(
                                "form.kellySuggest",
                                mapOf(
                                    "stake" to "%.2f".format(kelly.stake),
                                    "currency" to currency,
                                    "pct" to "%.1f".format(kelly.fraction * 100),
                                ),
                            )
                        } else {
                            tr("form.kellyNoEdge")
                        },
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
            }
        }
    }
}

@Composable
private fun LiabilityCalculatorCard(currency: String) {
    var stake by remember { mutableStateOf("") }
    var odds by remember { mutableStateOf("") }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(tr("android.liabilityTitle"), style = MaterialTheme.typography.titleMedium)
            AppTextField(stake, { stake = it }, tr("form.backersStake"), keyboardType = KeyboardType.Decimal)
            AppTextField(odds, { odds = it }, tr("android.layOdds"), keyboardType = KeyboardType.Decimal)

            val s = stake.toDoubleOrNull()
            val o = odds.toDoubleOrNull()
            val liability = if (s != null && o != null) BetMath.layLiability(s, o) else null
            if (liability != null) {
                Text(
                    "${tr("form.liability")}: ${formatMoney(liability, currency)}",
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(tr("form.backersStakeHint"), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

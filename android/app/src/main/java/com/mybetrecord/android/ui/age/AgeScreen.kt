package com.mybetrecord.android.ui.age

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.mybetrecord.android.R

@Composable
fun AgeAttestationScreen(
    onConfirmed: () -> Unit,
    onDeclined: () -> Unit,
    onConfirmClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.app_name),
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = stringResource(R.string.age_title),
            style = MaterialTheme.typography.headlineSmall,
        )
        Spacer(Modifier.height(12.dp))
        Text(
            text = stringResource(R.string.age_body),
            style = MaterialTheme.typography.bodyLarge,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            text = stringResource(R.string.disclaimer),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
        )
        Spacer(Modifier.height(24.dp))
        Button(
            onClick = {
                onConfirmClick()
                onConfirmed()
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.age_confirm))
        }
        Spacer(Modifier.height(8.dp))
        OutlinedButton(
            onClick = onDeclined,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(stringResource(R.string.age_decline))
        }
    }
}

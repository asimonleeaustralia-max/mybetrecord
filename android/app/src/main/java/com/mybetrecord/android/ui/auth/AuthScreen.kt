package com.mybetrecord.android.ui.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.R
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.ScreenScaffold
import com.mybetrecord.android.util.SecureWindowEffect

@Composable
fun AuthScreen(
    onLoggedIn: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel(),
) {
    SecureWindowEffect(enabled = true)
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.loggedIn) {
        if (state.loggedIn) onLoggedIn()
    }

    ScreenScaffold(
        padding = PaddingValues(0.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.app_name),
                style = MaterialTheme.typography.headlineLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = if (state.isRegister) stringResource(R.string.register) else stringResource(R.string.login),
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                text = stringResource(R.string.disclaimer),
                style = MaterialTheme.typography.bodySmall,
            )
            AppTextField(
                value = state.email,
                onValueChange = viewModel::onEmailChange,
                label = stringResource(R.string.email),
                enabled = !state.loading,
            )
            AppTextField(
                value = state.password,
                onValueChange = viewModel::onPasswordChange,
                label = stringResource(R.string.password),
                isPassword = true,
                enabled = !state.loading,
            )
            if (state.isRegister) {
                AppTextField(
                    value = state.confirmPassword,
                    onValueChange = viewModel::onConfirmPasswordChange,
                    label = "Confirm password",
                    isPassword = true,
                    enabled = !state.loading,
                )
            }
            state.error?.let { ErrorText(it) }
            state.info?.let {
                Text(it, color = MaterialTheme.colorScheme.secondary)
            }
            Button(
                onClick = viewModel::submit,
                enabled = !state.loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    if (state.loading) "Please wait…"
                    else if (state.isRegister) stringResource(R.string.register)
                    else stringResource(R.string.login),
                )
            }
            TextButton(onClick = viewModel::toggleMode, enabled = !state.loading) {
                Text(
                    if (state.isRegister) "Already have an account? Sign in"
                    else "Need an account? Register",
                )
            }
        }
    }
}

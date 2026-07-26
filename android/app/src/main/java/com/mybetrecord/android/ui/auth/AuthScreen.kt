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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.R
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.ScreenScaffold
import com.mybetrecord.android.util.SecureWindowEffect

@Composable
fun AuthScreen(
    onLoggedIn: () -> Unit,
    onForgotPassword: () -> Unit,
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
                text = if (state.isRegister) tr("auth.createAccount") else tr("auth.signIn"),
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                text = tr("auth.tagline"),
                style = MaterialTheme.typography.bodySmall,
            )
            AppTextField(
                value = state.email,
                onValueChange = viewModel::onEmailChange,
                label = tr("auth.email"),
                enabled = !state.loading,
            )
            AppTextField(
                value = state.password,
                onValueChange = viewModel::onPasswordChange,
                label = tr("auth.password"),
                isPassword = true,
                enabled = !state.loading,
            )
            if (state.isRegister) {
                AppTextField(
                    value = state.confirmPassword,
                    onValueChange = viewModel::onConfirmPasswordChange,
                    label = tr("auth.confirmPassword"),
                    isPassword = true,
                    enabled = !state.loading,
                )
            } else {
                TextButton(
                    onClick = onForgotPassword,
                    enabled = !state.loading,
                    modifier = Modifier.align(Alignment.End),
                ) {
                    Text(tr("auth.forgotPassword"))
                }
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
                    if (state.loading) tr("meta.signingIn")
                    else if (state.isRegister) tr("auth.createAccount")
                    else tr("auth.signIn"),
                )
            }
            TextButton(onClick = viewModel::toggleMode, enabled = !state.loading) {
                Text(
                    if (state.isRegister) tr("auth.signIn")
                    else tr("auth.createAccount"),
                )
            }
        }
    }
}

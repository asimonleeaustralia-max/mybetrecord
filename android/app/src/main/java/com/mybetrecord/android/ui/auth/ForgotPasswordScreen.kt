package com.mybetrecord.android.ui.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.SizeTransform
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.ui.components.AppTextField
import com.mybetrecord.android.ui.components.ErrorText
import com.mybetrecord.android.ui.components.ScreenScaffold
import com.mybetrecord.android.util.SecureWindowEffect

@Composable
fun ForgotPasswordScreen(
    onBackToSignIn: () -> Unit,
    viewModel: ForgotPasswordViewModel = hiltViewModel(),
) {
    SecureWindowEffect(enabled = true)
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenScaffold(
        padding = PaddingValues(0.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = tr("auth.forgotPassword"),
                style = MaterialTheme.typography.headlineSmall,
            )

            AnimatedContent(
                targetState = state.step,
                transitionSpec = {
                    (fadeIn() togetherWith fadeOut()).using(SizeTransform(clip = false))
                },
                label = "forgot-password-step",
            ) { step ->
                when (step) {
                    ResetStep.REQUEST -> RequestStep(state = state, viewModel = viewModel)
                    ResetStep.CONFIRM -> ConfirmStep(state = state, viewModel = viewModel)
                    ResetStep.DONE -> DoneStep(onBackToSignIn = onBackToSignIn)
                }
            }

            if (state.step != ResetStep.DONE) {
                TextButton(onClick = onBackToSignIn, enabled = !state.loading) {
                    Text(tr("auth.backToSignIn"))
                }
            }
        }
    }
}

@Composable
private fun RequestStep(state: ForgotPasswordUiState, viewModel: ForgotPasswordViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            text = tr("auth.forgotPasswordHint"),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        AppTextField(
            value = state.email,
            onValueChange = viewModel::onEmailChange,
            label = tr("auth.email"),
            enabled = !state.loading,
            keyboardType = KeyboardType.Email,
        )
        state.error?.let { ErrorText(it) }
        Button(
            onClick = viewModel::requestCode,
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(tr("auth.sendResetLink"))
        }
    }
}

@Composable
private fun ConfirmStep(state: ForgotPasswordUiState, viewModel: ForgotPasswordViewModel) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        state.info?.let {
            Text(
                text = it,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.secondary,
            )
        }
        AppTextField(
            value = state.code,
            onValueChange = viewModel::onCodeChange,
            label = tr("android.resetCode"),
            enabled = !state.loading,
            keyboardType = KeyboardType.Number,
        )
        AppTextField(
            value = state.newPassword,
            onValueChange = viewModel::onNewPasswordChange,
            label = tr("auth.newPassword"),
            isPassword = true,
            enabled = !state.loading,
        )
        AppTextField(
            value = state.confirmPassword,
            onValueChange = viewModel::onConfirmPasswordChange,
            label = tr("auth.confirmPassword"),
            isPassword = true,
            enabled = !state.loading,
        )
        state.error?.let { ErrorText(it) }
        Button(
            onClick = viewModel::confirmReset,
            enabled = !state.loading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(tr("auth.updatePassword"))
        }
        Column(horizontalAlignment = Alignment.Start) {
            TextButton(
                onClick = viewModel::resendCode,
                enabled = !state.loading && state.resendCooldownSeconds == 0,
            ) {
                Text(
                    if (state.resendCooldownSeconds > 0) {
                        tr("android.resendCodeIn", mapOf("s" to state.resendCooldownSeconds.toString()))
                    } else {
                        tr("android.resendCode")
                    },
                )
            }
            TextButton(onClick = viewModel::useDifferentEmail, enabled = !state.loading) {
                Text(tr("android.useDifferentEmail"))
            }
        }
    }
}

@Composable
private fun DoneStep(onBackToSignIn: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Icon(
            imageVector = Icons.Default.CheckCircle,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(48.dp),
        )
        Text(
            text = tr("auth.passwordUpdated"),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            text = tr("android.signInNewPassword"),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Button(onClick = onBackToSignIn, modifier = Modifier.fillMaxWidth()) {
            Text(tr("auth.backToSignIn"))
        }
    }
}

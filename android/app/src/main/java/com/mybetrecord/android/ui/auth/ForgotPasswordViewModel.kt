package com.mybetrecord.android.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.repository.AuthRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class ResetStep { REQUEST, CONFIRM, DONE }

private const val RESEND_COOLDOWN_SECONDS = 30

data class ForgotPasswordUiState(
    val step: ResetStep = ResetStep.REQUEST,
    val email: String = "",
    val code: String = "",
    val newPassword: String = "",
    val confirmPassword: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val info: String? = null,
    val resendCooldownSeconds: Int = 0,
)

@HiltViewModel
class ForgotPasswordViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ForgotPasswordUiState())
    val state: StateFlow<ForgotPasswordUiState> = _state.asStateFlow()

    private var cooldownJob: Job? = null

    fun onEmailChange(value: String) = _state.update { it.copy(email = value, error = null) }
    fun onCodeChange(value: String) = _state.update { it.copy(code = value, error = null) }
    fun onNewPasswordChange(value: String) = _state.update { it.copy(newPassword = value, error = null) }
    fun onConfirmPasswordChange(value: String) = _state.update { it.copy(confirmPassword = value, error = null) }

    /** Returns to the email step, e.g. if the user typed the wrong address. */
    fun useDifferentEmail() {
        cooldownJob?.cancel()
        _state.update {
            it.copy(
                step = ResetStep.REQUEST,
                code = "",
                newPassword = "",
                confirmPassword = "",
                error = null,
                info = null,
                resendCooldownSeconds = 0,
            )
        }
    }

    fun requestCode() {
        val email = _state.value.email.trim()
        if (email.isBlank() || !email.contains("@")) {
            _state.update { it.copy(error = "Enter a valid email address") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, info = null) }
            try {
                authRepository.requestPasswordReset(email)
                _state.update {
                    it.copy(
                        loading = false,
                        step = ResetStep.CONFIRM,
                        info = "If an account exists for $email, we've sent a reset code. It may take a minute to arrive.",
                    )
                }
                startCooldown()
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    fun resendCode() {
        if (_state.value.resendCooldownSeconds > 0 || _state.value.loading) return
        requestCode()
    }

    fun confirmReset() {
        val current = _state.value
        if (current.code.isBlank()) {
            _state.update { it.copy(error = "Enter the code we emailed you") }
            return
        }
        if (current.newPassword.length < 8) {
            _state.update { it.copy(error = "Password must be at least 8 characters") }
            return
        }
        if (current.newPassword != current.confirmPassword) {
            _state.update { it.copy(error = "Passwords do not match") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, info = null) }
            try {
                authRepository.confirmPasswordReset(current.code, current.newPassword)
                cooldownJob?.cancel()
                _state.update {
                    it.copy(
                        loading = false,
                        step = ResetStep.DONE,
                        info = "Your password has been updated.",
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    private fun startCooldown() {
        cooldownJob?.cancel()
        cooldownJob = viewModelScope.launch {
            for (remaining in RESEND_COOLDOWN_SECONDS downTo 1) {
                _state.update { it.copy(resendCooldownSeconds = remaining) }
                delay(1000)
            }
            _state.update { it.copy(resendCooldownSeconds = 0) }
        }
    }
}

package com.mybetrecord.android.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.repository.AuthRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.TimeZone
import javax.inject.Inject

data class AuthUiState(
    val email: String = "",
    val password: String = "",
    val confirmPassword: String = "",
    val isRegister: Boolean = false,
    val loading: Boolean = false,
    val error: String? = null,
    val info: String? = null,
    val loggedIn: Boolean = false,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState(loggedIn = authRepository.isLoggedIn()))
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    fun onEmailChange(value: String) = _state.update { it.copy(email = value, error = null) }
    fun onPasswordChange(value: String) = _state.update { it.copy(password = value, error = null) }
    fun onConfirmPasswordChange(value: String) = _state.update { it.copy(confirmPassword = value, error = null) }
    fun toggleMode() = _state.update {
        it.copy(isRegister = !it.isRegister, error = null, info = null)
    }

    fun submit() {
        val current = _state.value
        if (current.email.isBlank() || current.password.isBlank()) {
            _state.update { it.copy(error = "Email and password are required") }
            return
        }
        if (current.isRegister && current.password != current.confirmPassword) {
            _state.update { it.copy(error = "Passwords do not match") }
            return
        }
        if (current.isRegister && current.password.length < 8) {
            _state.update { it.copy(error = "Password must be at least 8 characters") }
            return
        }

        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null, info = null) }
            try {
                if (current.isRegister) {
                    val message = authRepository.register(
                        email = current.email,
                        password = current.password,
                        timezone = TimeZone.getDefault().id,
                    )
                    _state.update {
                        it.copy(
                            loading = false,
                            info = message.ifBlank {
                                "Check your email to verify your account, then sign in."
                            },
                            isRegister = false,
                            password = "",
                            confirmPassword = "",
                        )
                    }
                } else {
                    authRepository.login(current.email, current.password)
                    _state.update { it.copy(loading = false, loggedIn = true) }
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }
}

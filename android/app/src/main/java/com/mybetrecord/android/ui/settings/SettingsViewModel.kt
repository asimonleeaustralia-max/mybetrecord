package com.mybetrecord.android.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.SettingsUpdateDto
import com.mybetrecord.android.data.remote.UserDto
import com.mybetrecord.android.data.repository.AuthRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val loading: Boolean = true,
    val saving: Boolean = false,
    val error: String? = null,
    val info: String? = null,
    val user: UserDto? = null,
    val displayName: String = "",
    val baseCurrency: String = "GBP",
    val bankroll: String = "",
    val timezone: String = "",
    val defaultOddsFormat: String = "decimal",
    val showDeleteDialog: Boolean = false,
    val deletePassword: String = "",
    val deleteConfirm: String = "",
    val loggedOut: Boolean = false,
    val accountDeleted: Boolean = false,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                val user = authRepository.me()
                _state.update {
                    it.copy(
                        loading = false,
                        user = user,
                        displayName = user.displayName.orEmpty(),
                        baseCurrency = user.baseCurrency,
                        bankroll = user.bankroll.toString(),
                        timezone = user.timezone,
                        defaultOddsFormat = user.defaultOddsFormat,
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    fun update(transform: (SettingsUiState) -> SettingsUiState) = _state.update(transform)

    fun save() {
        val current = _state.value
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null, info = null) }
            try {
                val updated = authRepository.updateSettings(
                    SettingsUpdateDto(
                        displayName = current.displayName.trim().ifBlank { null },
                        baseCurrency = current.baseCurrency.trim().uppercase().takeIf { it.length == 3 },
                        bankroll = current.bankroll.toDoubleOrNull(),
                        timezone = current.timezone.trim().ifBlank { null },
                        defaultOddsFormat = current.defaultOddsFormat.trim().ifBlank { null },
                    ),
                )
                _state.update {
                    it.copy(
                        saving = false,
                        user = updated,
                        info = "Settings saved",
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(saving = false, error = t.toUserMessage()) }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _state.update { it.copy(loggedOut = true) }
        }
    }

    fun deleteAccount() {
        val current = _state.value
        if (current.deleteConfirm.trim().uppercase() != "DELETE") {
            _state.update { it.copy(error = "Type DELETE to confirm") }
            return
        }
        if (current.deletePassword.isBlank()) {
            _state.update { it.copy(error = "Password is required") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            try {
                authRepository.deleteAccount(current.deletePassword)
                _state.update { it.copy(saving = false, accountDeleted = true, showDeleteDialog = false) }
            } catch (t: Throwable) {
                _state.update { it.copy(saving = false, error = t.toUserMessage()) }
            }
        }
    }
}

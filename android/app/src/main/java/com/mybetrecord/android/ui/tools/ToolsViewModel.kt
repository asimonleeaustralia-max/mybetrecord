package com.mybetrecord.android.ui.tools

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.UserDto
import com.mybetrecord.android.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Loads the profile so the Kelly calculator can prefill bankroll and multiplier. */
@HiltViewModel
class ToolsViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _user = MutableStateFlow<UserDto?>(null)
    val user: StateFlow<UserDto?> = _user.asStateFlow()

    init {
        viewModelScope.launch {
            try {
                _user.value = authRepository.me()
            } catch (_: Throwable) {
                // Calculators still work without a profile; fields just start empty.
            }
        }
    }
}

package com.mybetrecord.android.ui.age

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.local.AppPreferences
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AgeViewModel @Inject constructor(
    private val prefs: AppPreferences,
) : ViewModel() {
    val ageAttested: StateFlow<Boolean?> = prefs.ageAttested
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun confirmAge() {
        viewModelScope.launch { prefs.setAgeAttested(true) }
    }
}

package com.mybetrecord.android.ui.bets

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class BetsListUiState(
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class BetsListViewModel @Inject constructor(
    private val betsRepository: BetsRepository,
) : ViewModel() {
    val bets: StateFlow<List<BetDto>> = betsRepository.observeCachedBets()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _state = MutableStateFlow(BetsListUiState())
    val state: StateFlow<BetsListUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _state.update { it.copy(refreshing = true, error = null) }
            try {
                betsRepository.refreshBets()
                _state.update { it.copy(refreshing = false) }
            } catch (t: Throwable) {
                _state.update { it.copy(refreshing = false, error = t.toUserMessage()) }
            }
        }
    }

    fun delete(id: String) {
        viewModelScope.launch {
            try {
                betsRepository.deleteBet(id)
            } catch (t: Throwable) {
                _state.update { it.copy(error = t.toUserMessage()) }
            }
        }
    }
}

data class BetEditorUiState(
    val loading: Boolean = false,
    val saving: Boolean = false,
    val error: String? = null,
    val saved: Boolean = false,
    val deleted: Boolean = false,
    val sport: String = "Football",
    val event: String = "",
    val selection: String = "",
    val odds: String = "",
    val stake: String = "",
    val currency: String = "GBP",
    val betType: String = "Win",
    val outcome: String = "pending",
    val bookmaker: String = "",
    val notes: String = "",
    val isEdit: Boolean = false,
)

@HiltViewModel
class BetEditorViewModel @Inject constructor(
    private val betsRepository: BetsRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val betId: String? = savedStateHandle.get<String>("betId")?.takeIf { it != "new" }

    private val _state = MutableStateFlow(BetEditorUiState(isEdit = betId != null))
    val state: StateFlow<BetEditorUiState> = _state.asStateFlow()

    init {
        if (betId != null) load(betId)
    }

    private fun load(id: String) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            try {
                val bet = betsRepository.getBet(id)
                _state.update {
                    it.copy(
                        loading = false,
                        sport = bet.sport,
                        event = bet.event,
                        selection = bet.selection,
                        odds = bet.oddsDecimal.toString(),
                        stake = bet.stake.toString(),
                        currency = bet.currency,
                        betType = bet.betType,
                        outcome = bet.outcome,
                        bookmaker = bet.bookmaker.orEmpty(),
                        notes = bet.notes.orEmpty(),
                    )
                }
            } catch (t: Throwable) {
                _state.update { it.copy(loading = false, error = t.toUserMessage()) }
            }
        }
    }

    fun update(transform: (BetEditorUiState) -> BetEditorUiState) {
        _state.update(transform)
    }

    fun save() {
        val current = _state.value
        val odds = current.odds.toDoubleOrNull()
        val stake = current.stake.toDoubleOrNull()
        if (current.event.isBlank() || current.selection.isBlank() || odds == null || stake == null) {
            _state.update { it.copy(error = "Event, selection, odds and stake are required") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            try {
                if (betId == null) {
                    betsRepository.createBet(
                        BetCreateDto(
                            sport = current.sport.trim(),
                            event = current.event.trim(),
                            selection = current.selection.trim(),
                            odds = odds,
                            stake = stake,
                            currency = current.currency.trim().ifBlank { "GBP" },
                            betType = current.betType.trim().ifBlank { "Win" },
                            outcome = current.outcome.trim().ifBlank { "pending" },
                            bookmaker = current.bookmaker.trim().ifBlank { null },
                            notes = current.notes.trim().ifBlank { null },
                        ),
                    )
                } else {
                    betsRepository.updateBet(
                        betId,
                        BetUpdateDto(
                            sport = current.sport.trim(),
                            event = current.event.trim(),
                            selection = current.selection.trim(),
                            odds = odds,
                            stake = stake,
                            currency = current.currency.trim().ifBlank { "GBP" },
                            betType = current.betType.trim().ifBlank { "Win" },
                            outcome = current.outcome.trim().ifBlank { "pending" },
                            bookmaker = current.bookmaker.trim().ifBlank { null },
                            notes = current.notes.trim().ifBlank { null },
                        ),
                    )
                }
                _state.update { it.copy(saving = false, saved = true) }
            } catch (t: Throwable) {
                _state.update { it.copy(saving = false, error = t.toUserMessage()) }
            }
        }
    }

    fun delete() {
        val id = betId ?: return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            try {
                betsRepository.deleteBet(id)
                _state.update { it.copy(saving = false, deleted = true) }
            } catch (t: Throwable) {
                _state.update { it.copy(saving = false, error = t.toUserMessage()) }
            }
        }
    }
}

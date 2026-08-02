package com.mybetrecord.android.ui.bets

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mybetrecord.android.data.remote.BetCreateDto
import com.mybetrecord.android.data.remote.BetDto
import com.mybetrecord.android.data.remote.BetLegCreateDto
import com.mybetrecord.android.data.remote.BetUpdateDto
import com.mybetrecord.android.data.repository.BetsRepository
import com.mybetrecord.android.i18n.tr
import com.mybetrecord.android.util.BetMath
import com.mybetrecord.android.util.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.IOException
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import javax.inject.Inject

data class BetsListUiState(
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    /** Bets whose result is mid-save, so their row can show progress. */
    val settling: Set<String> = emptySet(),
)

/**
 * Results selectable for a bet, mirroring the web's BET_OUTCOMES: each-way bets
 * swap the Asian-handicap halves for "placed".
 */
fun outcomeOptions(eachWay: Boolean): List<String> = if (eachWay) {
    listOf("pending", "win", "placed", "loss", "void")
} else {
    listOf("pending", "win", "loss", "void", "half_win", "half_loss")
}

/** An each-way bet whose place part came in reads as "placed", not "loss". */
fun displayOutcome(bet: BetDto): String =
    if (bet.eachWay && bet.placed && bet.outcome == "loss") "placed" else bet.outcome

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
            } catch (t: IOException) {
                // The cached ledger is already on screen and the sync banner
                // explains the state, so a connection drop is not an error here.
                _state.update { it.copy(refreshing = false) }
            } catch (t: Throwable) {
                _state.update { it.copy(refreshing = false, error = t.toUserMessage()) }
            }
        }
    }

    /** Settles a bet straight from the ledger — the app's quickest way to record a result. */
    fun setOutcome(id: String, outcome: String) {
        viewModelScope.launch {
            _state.update { it.copy(settling = it.settling + id, error = null) }
            try {
                betsRepository.setOutcome(id, outcome)
            } catch (t: Throwable) {
                _state.update { it.copy(error = t.toUserMessage()) }
            } finally {
                _state.update { it.copy(settling = it.settling - id) }
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

/** One editable selection of a multiple. Odds text is in the bet's odds format. */
data class LegInput(
    val event: String = "",
    val selection: String = "",
    val odds: String = "",
)

data class BetEditorUiState(
    val loading: Boolean = false,
    val saving: Boolean = false,
    val error: String? = null,
    val saved: Boolean = false,
    val deleted: Boolean = false,
    val sport: String = "Football",
    val event: String = "",
    val selection: String = "",
    val oddsFormat: String = "decimal",
    val odds: String = "",
    val stake: String = "",
    val currency: String = "GBP",
    val betType: String = "Win",
    val outcome: String = "pending",
    val bookmaker: String = "",
    val portal: String = "",
    val tipster: String = "",
    val notes: String = "",
    val eachWay: Boolean = false,
    val freeBet: Boolean = false,
    val cashOut: String = "",
    val eventAt: String = "",
    val closingOdds: String = "",
    val isMultiple: Boolean = false,
    val legs: List<LegInput> = listOf(LegInput(), LegInput()),
    val clvPct: Double? = null,
    val shareToken: String? = null,
    val sharing: Boolean = false,
    val isEdit: Boolean = false,
)

private val EVENT_AT_INPUT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")

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
                        // The API stores only decimal odds, so edits always re-open in decimal.
                        oddsFormat = "decimal",
                        odds = bet.oddsDecimal.toString(),
                        stake = bet.stake.toString(),
                        currency = bet.currency,
                        betType = bet.betType,
                        outcome = bet.outcome,
                        bookmaker = bet.bookmaker.orEmpty(),
                        portal = bet.portal.orEmpty(),
                        tipster = bet.tipster.orEmpty(),
                        notes = bet.notes.orEmpty(),
                        eachWay = bet.eachWay,
                        freeBet = bet.freeBet,
                        cashOut = bet.cashOutAmount?.toString().orEmpty(),
                        eventAt = formatEventAt(bet.eventAt),
                        closingOdds = bet.closingOdds?.toString().orEmpty(),
                        isMultiple = bet.isMultiple,
                        legs = if (bet.isMultiple && bet.legs.isNotEmpty()) {
                            bet.legs.map { leg ->
                                LegInput(leg.event, leg.selection, leg.oddsDecimal.toString())
                            }
                        } else {
                            it.legs
                        },
                        clvPct = bet.clvPct,
                        shareToken = bet.shareToken,
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

    fun addLeg() {
        _state.update { s ->
            if (s.legs.size >= 10) s else s.copy(legs = s.legs + LegInput())
        }
    }

    fun removeLeg(index: Int) {
        _state.update { s ->
            if (s.legs.size <= 2) s else s.copy(legs = s.legs.filterIndexed { i, _ -> i != index })
        }
    }

    fun updateLeg(index: Int, transform: (LegInput) -> LegInput) {
        _state.update { s ->
            s.copy(legs = s.legs.mapIndexed { i, leg -> if (i == index) transform(leg) else leg })
        }
    }

    /** Decimal odds implied by the current inputs, for previews (combined odds, liability). */
    fun currentDecimalOdds(): Double? {
        val s = _state.value
        return if (s.isMultiple) {
            BetMath.combinedOdds(s.legs.mapNotNull { parseOddsToDecimal(it.odds, s.oddsFormat) })
        } else {
            parseOddsToDecimal(s.odds, s.oddsFormat)
        }
    }

    private fun parseOddsToDecimal(text: String, format: String): Double? {
        if (text.isBlank()) return null
        return if (format == "fractional") {
            BetMath.parseFractional(text)?.let { (n, d) -> BetMath.fractionalToDecimal(n, d) }
        } else {
            text.toDoubleOrNull()?.takeIf { it > 1 }
        }
    }

    /** Returns odds (value, denominator) as the API expects them, or null when invalid. */
    private fun oddsForApi(text: String, format: String): Pair<Double, Double?>? {
        return if (format == "fractional") {
            BetMath.parseFractional(text)?.let { (n, d) -> n to d }
        } else {
            text.toDoubleOrNull()?.takeIf { it > 1 }?.let { it to null }
        }
    }

    private fun parseEventAt(text: String): String? {
        if (text.isBlank()) return null
        return LocalDateTime.parse(text.trim(), EVENT_AT_INPUT)
            .format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
    }

    private fun formatEventAt(iso: String?): String {
        if (iso.isNullOrBlank()) return ""
        return try {
            LocalDateTime
                .parse(iso.take(16), DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm"))
                .format(EVENT_AT_INPUT)
        } catch (_: Exception) {
            ""
        }
    }

    fun save() {
        val current = _state.value
        val stake = current.stake.toDoubleOrNull()

        val eventAtIso = try {
            parseEventAt(current.eventAt)
        } catch (_: Exception) {
            _state.update { it.copy(error = tr("android.invalidEventAt")) }
            return
        }

        val legsForApi: List<BetLegCreateDto>?
        val odds: Pair<Double, Double?>?
        if (current.isMultiple) {
            odds = null
            val parsed = current.legs.map { leg ->
                if (leg.event.isBlank() || leg.selection.isBlank()) {
                    _state.update { it.copy(error = tr("form.legMissingFields")) }
                    return
                }
                val legOdds = oddsForApi(leg.odds, current.oddsFormat)
                if (legOdds == null) {
                    _state.update { it.copy(error = tr("form.legBadOdds")) }
                    return
                }
                BetLegCreateDto(
                    event = leg.event.trim(),
                    selection = leg.selection.trim(),
                    odds = legOdds.first,
                    oddsFormat = current.oddsFormat,
                    oddsDenominator = legOdds.second,
                )
            }
            if (parsed.size < 2) {
                _state.update { it.copy(error = tr("form.needTwoLegs")) }
                return
            }
            legsForApi = parsed
            if (stake == null) {
                _state.update { it.copy(error = tr("android.requiredFields")) }
                return
            }
        } else {
            legsForApi = null
            odds = oddsForApi(current.odds, current.oddsFormat)
            if (current.event.isBlank() || current.selection.isBlank() || odds == null || stake == null) {
                _state.update {
                    it.copy(
                        error = if (current.oddsFormat == "fractional" && current.odds.isNotBlank() &&
                            BetMath.parseFractional(current.odds) == null
                        ) {
                            tr("android.invalidFractional")
                        } else {
                            tr("android.requiredFields")
                        },
                    )
                }
                return
            }
        }

        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            try {
                if (betId == null) {
                    betsRepository.createBet(
                        BetCreateDto(
                            sport = current.sport.trim(),
                            event = current.event.trim().ifBlank { null },
                            selection = current.selection.trim().ifBlank { null },
                            odds = odds?.first,
                            oddsDenominator = odds?.second,
                            oddsFormat = current.oddsFormat,
                            stake = stake,
                            currency = current.currency.trim().uppercase().ifBlank { "GBP" },
                            betType = current.betType.trim().ifBlank { "Win" },
                            outcome = current.outcome.trim().ifBlank { "pending" },
                            bookmaker = current.bookmaker.trim().ifBlank { null },
                            portal = current.portal.ifBlank { null },
                            tipster = current.tipster.trim().ifBlank { null },
                            notes = current.notes.trim().ifBlank { null },
                            eachWay = !current.isMultiple && current.eachWay,
                            freeBet = !current.isMultiple && current.freeBet,
                            cashOutAmount = current.cashOut.toDoubleOrNull(),
                            eventAt = eventAtIso,
                            closingOdds = current.closingOdds.toDoubleOrNull(),
                            isMultiple = current.isMultiple,
                            legs = legsForApi,
                        ),
                    )
                } else {
                    betsRepository.updateBet(
                        betId,
                        BetUpdateDto(
                            sport = current.sport.trim(),
                            event = current.event.trim().ifBlank { null },
                            selection = current.selection.trim().ifBlank { null },
                            odds = odds?.first,
                            oddsDenominator = odds?.second,
                            oddsFormat = current.oddsFormat,
                            stake = stake,
                            currency = current.currency.trim().uppercase().ifBlank { "GBP" },
                            betType = current.betType.trim().ifBlank { "Win" },
                            outcome = current.outcome.trim().ifBlank { "pending" },
                            bookmaker = current.bookmaker.trim().ifBlank { null },
                            portal = current.portal.ifBlank { null },
                            tipster = current.tipster.trim().ifBlank { null },
                            notes = current.notes.trim().ifBlank { null },
                            eachWay = !current.isMultiple && current.eachWay,
                            freeBet = !current.isMultiple && current.freeBet,
                            cashOutAmount = current.cashOut.toDoubleOrNull(),
                            eventAt = eventAtIso,
                            closingOdds = current.closingOdds.toDoubleOrNull(),
                            isMultiple = current.isMultiple,
                            legs = legsForApi,
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

    fun createShareLink() {
        val id = betId ?: return
        viewModelScope.launch {
            _state.update { it.copy(sharing = true, error = null) }
            try {
                val token = betsRepository.createShareLink(id)
                _state.update { it.copy(sharing = false, shareToken = token) }
            } catch (t: Throwable) {
                _state.update { it.copy(sharing = false, error = t.toUserMessage()) }
            }
        }
    }

    fun revokeShareLink() {
        val id = betId ?: return
        viewModelScope.launch {
            _state.update { it.copy(sharing = true, error = null) }
            try {
                betsRepository.revokeShareLink(id)
                _state.update { it.copy(sharing = false, shareToken = null) }
            } catch (t: Throwable) {
                _state.update { it.copy(sharing = false, error = t.toUserMessage()) }
            }
        }
    }
}

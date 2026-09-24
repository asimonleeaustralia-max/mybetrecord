import Foundation

struct LegInput: Identifiable, Equatable {
    let id = UUID()
    var event = ""
    var selection = ""
    var odds = ""
}

@MainActor
final class BetEditorModel: ObservableObject {
    @Published var loading = false
    @Published var saving = false
    @Published var errorMessage: String?
    @Published var warningMessage: String?
    @Published var saved = false
    @Published var deleted = false

    @Published var sport = "Soccer"
    @Published var event = ""
    @Published var selection = ""
    @Published var oddsFormat = "decimal"
    @Published var odds = ""
    @Published var stake = ""
    @Published var currency = "GBP"
    @Published var betType = "Win"
    @Published var side = "back"
    @Published var outcome = "pending"
    @Published var bookmaker = ""
    @Published var portal = ""
    @Published var tipster = ""
    @Published var betBroker = ""
    @Published var notes = ""
    @Published var tournament = ""
    @Published var eachWay = false
    @Published var freeBet = false
    @Published var placeFraction = "0.25"
    @Published var exchangeCommission = ""
    @Published var cashOut = ""
    @Published var eventAt = ""
    @Published var placedAt = ""
    @Published var settledAt = ""
    @Published var closingOdds = ""
    @Published var closingOddsExchange = ""
    @Published var betModel = ""
    @Published var personalImpliedOdds = ""
    @Published var modelImpliedOdds = ""
    @Published var tipsterImpliedOdds = ""
    @Published var isMultiple = false
    @Published var legs: [LegInput] = [LegInput(), LegInput()]
    @Published var shareToken: String?
    @Published var sharing = false
    @Published var clvPct: Double?
    @Published var bankroll: Double = 0
    @Published var kellyMultiplier: Double = 1
    @Published var sportSuggestions: [String] = BetCatalog.choices(catalog: BetCatalog.sports)
    @Published var betTypeSuggestions: [String] = BetCatalog.choices(catalog: BetCatalog.betTypes)
    @Published var bookmakerSuggestions: [String] = BetCatalog.choices(catalog: BetCatalog.bookmakers)

    let betId: String?
    let isEdit: Bool
    private let betsRepository: BetsRepository
    private let authRepository: AuthRepository?

    init(betId: String?, betsRepository: BetsRepository, authRepository: AuthRepository? = nil) {
        self.betId = betId == "new" ? nil : betId
        self.isEdit = betId != nil && betId != "new"
        self.betsRepository = betsRepository
        self.authRepository = authRepository
        applyCachedSuggestionExtras()
        if let id = self.betId {
            Task { await load(id: id) }
        } else {
            placedAt = Self.nowLocal()
            Task { await applyUserDefaults() }
        }
        Task { await refreshSuggestionExtras() }
    }

    private func applyUserDefaults() async {
        guard let authRepository else { return }
        do {
            let user = try await authRepository.me()
            if !isEdit {
                currency = user.baseCurrency
                oddsFormat = user.defaultOddsFormat
            }
            bankroll = user.bankroll
            kellyMultiplier = user.kellyMultiplier
        } catch {
            // Defaults already set; editing can continue without profile prefs.
        }
    }

    private func applyCachedSuggestionExtras() {
        let cached = (try? betsRepository.cachedBets()) ?? []
        let sports = cached.map(\.sport)
        let betTypes = cached.map(\.betType)
        let bookmakers = cached.compactMap(\.bookmaker)
        sportSuggestions = BetCatalog.choices(catalog: BetCatalog.sports, extras: sports)
        betTypeSuggestions = BetCatalog.choices(catalog: BetCatalog.betTypes, extras: betTypes)
        bookmakerSuggestions = BetCatalog.choices(catalog: BetCatalog.bookmakers, extras: bookmakers)
    }

    private func refreshSuggestionExtras() async {
        applyCachedSuggestionExtras()
        async let sportsTask = betsRepository.listSports()
        async let betTypesTask = betsRepository.listBetTypes()
        let remoteSports = (try? await sportsTask) ?? []
        let remoteBetTypes = (try? await betTypesTask) ?? []
        let cached = (try? betsRepository.cachedBets()) ?? []
        sportSuggestions = BetCatalog.choices(
            catalog: BetCatalog.sports,
            extras: remoteSports + cached.map(\.sport)
        )
        betTypeSuggestions = BetCatalog.choices(
            catalog: BetCatalog.betTypes,
            extras: remoteBetTypes + cached.map(\.betType)
        )
        bookmakerSuggestions = BetCatalog.choices(
            catalog: BetCatalog.bookmakers,
            extras: cached.compactMap(\.bookmaker)
        )
    }

    func load(id: String) async {
        loading = true
        defer { loading = false }
        do {
            async let betTask = betsRepository.getBet(id: id)
            async let userTask: User? = {
                guard let authRepository else { return nil }
                return try? await authRepository.me()
            }()
            let bet = try await betTask
            if let user = await userTask {
                bankroll = user.bankroll
                kellyMultiplier = user.kellyMultiplier
            }
            apply(bet)
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    private func apply(_ bet: Bet) {
        sport = bet.sport
        event = bet.event
        selection = bet.selection
        let fmt = BetMath.oddsFormats.contains(bet.oddsFormat) ? bet.oddsFormat : "decimal"
        oddsFormat = fmt
        odds = BetMath.formatFromDecimal(bet.oddsDecimal, format: fmt)
        stake = String(bet.stake)
        currency = bet.currency
        betType = bet.betType
        side = bet.side
        bookmaker = bet.bookmaker ?? ""
        portal = bet.portal ?? ""
        tipster = bet.tipster ?? ""
        betBroker = bet.betBroker ?? ""
        notes = bet.notes ?? ""
        tournament = bet.tournament ?? ""
        eachWay = bet.eachWay
        freeBet = bet.freeBet
        placeFraction = String(bet.placeFraction)
        exchangeCommission = bet.exchangeCommissionPct.map { String($0) } ?? ""
        cashOut = bet.cashOutAmount.map { String($0) } ?? ""
        eventAt = Self.formatDateTime(bet.eventAt)
        placedAt = Self.formatDateTime(bet.placedAt)
        settledAt = bet.outcome != "pending" ? Self.formatDateTime(bet.settledAt) : ""
        closingOdds = bet.closingOdds.map { String($0) } ?? ""
        closingOddsExchange = bet.closingOddsExchange.map { String($0) } ?? ""
        betModel = bet.betModel ?? ""
        personalImpliedOdds = bet.personalImpliedOdds.map { String($0) } ?? ""
        modelImpliedOdds = bet.modelImpliedOdds.map { String($0) } ?? ""
        tipsterImpliedOdds = bet.tipsterImpliedOdds.map { String($0) } ?? ""
        isMultiple = bet.isMultiple
        if bet.isMultiple, !bet.legs.isEmpty {
            let legFmt = BetMath.oddsFormats.contains(bet.legs[0].oddsFormat) ? bet.legs[0].oddsFormat : fmt
            oddsFormat = legFmt
            legs = bet.legs.map {
                LegInput(event: $0.event, selection: $0.selection, odds: BetMath.formatFromDecimal($0.oddsDecimal, format: legFmt))
            }
        }
        outcome = Self.displayOutcome(bet)
        shareToken = bet.shareToken
        clvPct = bet.clvPct
    }

    func setOddsFormat(_ next: String) {
        guard next != oddsFormat else { return }
        if isMultiple {
            legs = legs.map { leg in
                var copy = leg
                if let dec = BetMath.toDecimal(leg.odds, format: oddsFormat) {
                    copy.odds = BetMath.formatFromDecimal(dec, format: next)
                }
                return copy
            }
        } else if let dec = BetMath.toDecimal(odds, format: oddsFormat) {
            odds = BetMath.formatFromDecimal(dec, format: next)
        }
        oddsFormat = next
    }

    func setMultiple(_ enabled: Bool) {
        isMultiple = enabled
        if enabled {
            side = "back"
            eachWay = false
            freeBet = false
        }
    }

    func setSide(_ value: String) {
        side = value
        if value == "lay" {
            eachWay = false
            freeBet = false
        }
    }

    func setEachWay(_ enabled: Bool) {
        eachWay = enabled
        let valid = Set(availableOutcomes.map(\.self))
        if !valid.contains(outcome) {
            outcome = "pending"
        }
    }

    func addLeg() {
        guard legs.count < 10 else { return }
        legs.append(LegInput())
    }

    func removeLeg(at index: Int) {
        guard legs.count > 2, legs.indices.contains(index) else { return }
        legs.remove(at: index)
    }

    var availableOutcomes: [String] {
        if eachWay && !isMultiple {
            return ["pending", "win", "placed", "loss", "void"]
        }
        return ["pending", "win", "loss", "void", "half_win", "half_loss"]
    }

    var isLay: Bool { side == "lay" && !isMultiple }

    var canUsePromotions: Bool { !isMultiple && !isLay }

    func currentDecimalOdds() -> Double? {
        if isMultiple {
            let values = legs.compactMap { BetMath.toDecimal($0.odds, format: oddsFormat) }
            return BetMath.combinedOdds(values)
        }
        return BetMath.toDecimal(odds, format: oddsFormat)
    }

    func settlementProfitPreview() -> Double? {
        guard let stakeValue = Double(stake), stakeValue > 0 else { return nil }
        let cashOutValue = cashOut.trimmingCharacters(in: .whitespaces).isEmpty ? nil : Double(cashOut)
        let settled = outcome != "pending" || cashOutValue != nil
        guard settled else { return nil }
        let oddsDec = currentDecimalOdds() ?? 0
        return BetMath.settleProfit(
            stake: stakeValue,
            oddsDecimal: oddsDec,
            outcome: outcome,
            eachWay: !isMultiple && eachWay,
            placeFraction: Double(placeFraction) ?? 0.25,
            side: isMultiple ? "back" : side,
            freeBet: !isMultiple && freeBet,
            exchangeCommissionPct: Double(exchangeCommission) ?? 0,
            cashOutAmount: cashOutValue
        )
    }

    func liabilityPreview() -> Double? {
        guard isLay, let stakeValue = Double(stake), let oddsDec = currentDecimalOdds() else { return nil }
        return BetMath.layLiability(backersStake: stakeValue, oddsDecimal: oddsDec)
    }

    func effectiveOddsPreview() -> Double? {
        guard !isLay, let oddsDec = currentDecimalOdds(), let commission = Double(exchangeCommission) else { return nil }
        return BetMath.effectiveDecimalOdds(oddsDecimal: oddsDec, commissionPct: commission)
    }

    func cashOutExceedsMax() -> Bool {
        guard let cashOutValue = Double(cashOut),
              let stakeValue = Double(stake),
              let oddsDec = currentDecimalOdds(),
              let maxReturn = BetMath.maxCashOutReturn(stake: stakeValue, oddsDecimal: oddsDec, freeBet: freeBet)
        else { return false }
        return cashOutValue > maxReturn + 0.001
    }

    func personalEdge() -> Double? {
        guard let oddsDec = currentDecimalOdds(), let implied = Double(personalImpliedOdds) else { return nil }
        return BetMath.edgePct(oddsDecimal: oddsDec, impliedDecimal: implied)
    }

    func modelEdge() -> Double? {
        guard let oddsDec = currentDecimalOdds(), let implied = Double(modelImpliedOdds) else { return nil }
        return BetMath.edgePct(oddsDecimal: oddsDec, impliedDecimal: implied)
    }

    func tipsterEdge() -> Double? {
        guard let oddsDec = currentDecimalOdds(), let implied = Double(tipsterImpliedOdds) else { return nil }
        return BetMath.edgePct(oddsDecimal: oddsDec, impliedDecimal: implied)
    }

    func personalKelly() -> BetMath.KellyResult? {
        guard let oddsDec = currentDecimalOdds(), let implied = Double(personalImpliedOdds) else { return nil }
        return BetMath.kelly(oddsDecimal: oddsDec, impliedDecimal: implied, bankroll: bankroll, multiplier: kellyMultiplier)
    }

    func modelKelly() -> BetMath.KellyResult? {
        guard let oddsDec = currentDecimalOdds(), let implied = Double(modelImpliedOdds) else { return nil }
        return BetMath.kelly(oddsDecimal: oddsDec, impliedDecimal: implied, bankroll: bankroll, multiplier: kellyMultiplier)
    }

    func computedClv() -> Double? {
        guard let oddsDec = currentDecimalOdds(), let closing = Double(closingOdds) else { return clvPct }
        return BetMath.clvPct(takenDecimal: oddsDec, closingDecimal: closing)
    }

    func save() async {
        warningMessage = nil
        errorMessage = nil

        let currencyValue = currency.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard currencyValue.range(of: "^[A-Z]{3}$", options: .regularExpression) != nil else {
            errorMessage = tr("form.invalidCurrency")
            return
        }

        guard let stakeValue = Double(stake), stakeValue > 0 else {
            errorMessage = tr("form.requiredFields")
            return
        }

        let eventAtIso: String?
        let placedAtIso: String?
        let settledAtIso: String?
        do {
            eventAtIso = try Self.parseDateTime(eventAt, required: false)
            placedAtIso = try Self.parseDateTime(placedAt, required: false) ?? Self.nowIso()
            if outcome != "pending" || !cashOut.trimmingCharacters(in: .whitespaces).isEmpty {
                settledAtIso = try Self.parseDateTime(settledAt, required: false) ?? Self.nowIso()
            } else {
                settledAtIso = try Self.parseDateTime(settledAt, required: false)
            }
        } catch {
            errorMessage = tr("form.invalidDateTime")
            return
        }

        var legsForApi: [BetLegCreate]?
        var oddsPair: (Double, Double?)?
        if isMultiple {
            var parsed: [BetLegCreate] = []
            for leg in legs {
                guard !leg.event.trimmingCharacters(in: .whitespaces).isEmpty,
                      !leg.selection.trimmingCharacters(in: .whitespaces).isEmpty else {
                    errorMessage = tr("form.legMissingFields")
                    return
                }
                guard let legOdds = BetMath.oddsForApi(leg.odds, format: oddsFormat) else {
                    errorMessage = tr("form.legBadOdds")
                    return
                }
                parsed.append(BetLegCreate(
                    event: leg.event.trimmingCharacters(in: .whitespaces),
                    selection: leg.selection.trimmingCharacters(in: .whitespaces),
                    odds: legOdds.0,
                    oddsFormat: oddsFormat,
                    oddsDenominator: legOdds.1
                ))
            }
            guard parsed.count >= 2 else {
                errorMessage = tr("form.needTwoLegs")
                return
            }
            legsForApi = parsed
        } else {
            guard !event.trimmingCharacters(in: .whitespaces).isEmpty,
                  !selection.trimmingCharacters(in: .whitespaces).isEmpty,
                  let pair = BetMath.oddsForApi(odds, format: oddsFormat) else {
                if oddsFormat == "fractional", !odds.isEmpty, BetMath.parseFractional(odds) == nil {
                    errorMessage = tr("form.invalidFractional")
                } else {
                    errorMessage = tr("form.requiredFields")
                }
                return
            }
            oddsPair = pair
        }

        if cashOutExceedsMax() {
            warningMessage = tr("form.cashOutExceedsMax")
        }

        let useEachWay = !isMultiple && !isLay && eachWay
        let useFreeBet = !isMultiple && !isLay && freeBet
        let placed = useEachWay && (outcome == "win" || outcome == "placed")
        let sideValue = isMultiple ? "back" : side

        saving = true
        defer { saving = false }
        do {
            if let betId {
                let update = BetUpdate(
                    sport: sport.trimmingCharacters(in: .whitespaces),
                    event: isMultiple ? nil : event.nilIfBlank,
                    selection: isMultiple ? nil : selection.nilIfBlank,
                    odds: oddsPair?.0,
                    stake: stakeValue,
                    betType: betType.trimmingCharacters(in: .whitespaces).nilIfBlank ?? "Win",
                    side: sideValue,
                    currency: currencyValue,
                    oddsFormat: oddsFormat,
                    oddsDenominator: oddsPair?.1,
                    outcome: outcome,
                    tournament: tournament.nilIfBlank,
                    bookmaker: bookmaker.nilIfBlank,
                    portal: portal.nilIfBlank,
                    exchangeCommissionPct: Double(exchangeCommission) ?? 0,
                    tipster: tipster.nilIfBlank,
                    betBroker: betBroker.nilIfBlank,
                    notes: notes.nilIfBlank,
                    eachWay: useEachWay,
                    placeFraction: useEachWay ? (Double(placeFraction) ?? 0.25) : nil,
                    placed: placed,
                    freeBet: useFreeBet,
                    isMultiple: isMultiple,
                    legs: legsForApi,
                    cashOutAmount: Double(cashOut),
                    betModel: betModel.nilIfBlank,
                    modelImpliedOdds: Double(modelImpliedOdds),
                    personalImpliedOdds: Double(personalImpliedOdds),
                    tipsterImpliedOdds: Double(tipsterImpliedOdds),
                    closingOdds: Double(closingOdds),
                    closingOddsExchange: Double(closingOddsExchange),
                    eventAt: eventAtIso,
                    placedAt: placedAtIso,
                    settledAt: settledAtIso
                )
                _ = try await betsRepository.updateBet(id: betId, body: update)
            } else {
                let create = BetCreate(
                    sport: sport.trimmingCharacters(in: .whitespaces),
                    event: isMultiple ? nil : event.nilIfBlank,
                    selection: isMultiple ? nil : selection.nilIfBlank,
                    odds: oddsPair?.0,
                    stake: stakeValue,
                    betType: betType.trimmingCharacters(in: .whitespaces).nilIfBlank ?? "Win",
                    side: sideValue,
                    currency: currencyValue,
                    oddsFormat: oddsFormat,
                    oddsDenominator: oddsPair?.1,
                    outcome: outcome,
                    tournament: tournament.nilIfBlank,
                    bookmaker: bookmaker.nilIfBlank,
                    portal: portal.nilIfBlank,
                    exchangeCommissionPct: Double(exchangeCommission) ?? 0,
                    tipster: tipster.nilIfBlank,
                    betBroker: betBroker.nilIfBlank,
                    notes: notes.nilIfBlank,
                    eachWay: useEachWay,
                    placeFraction: useEachWay ? (Double(placeFraction) ?? 0.25) : 0.25,
                    placed: placed,
                    freeBet: useFreeBet,
                    isMultiple: isMultiple,
                    legs: legsForApi,
                    cashOutAmount: Double(cashOut),
                    betModel: betModel.nilIfBlank,
                    modelImpliedOdds: Double(modelImpliedOdds),
                    personalImpliedOdds: Double(personalImpliedOdds),
                    tipsterImpliedOdds: Double(tipsterImpliedOdds),
                    closingOdds: Double(closingOdds),
                    closingOddsExchange: Double(closingOddsExchange),
                    placedAt: placedAtIso,
                    eventAt: eventAtIso,
                    settledAt: settledAtIso
                )
                _ = try await betsRepository.createBet(create)
            }
            saved = true
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    func delete() async {
        guard let betId else { return }
        saving = true
        defer { saving = false }
        do {
            try await betsRepository.deleteBet(id: betId)
            deleted = true
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    func createShareLink() async {
        guard let betId else { return }
        sharing = true
        defer { sharing = false }
        do {
            shareToken = try await betsRepository.createShareLink(id: betId)
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    func revokeShareLink() async {
        guard let betId else { return }
        sharing = true
        defer { sharing = false }
        do {
            try await betsRepository.revokeShareLink(id: betId)
            shareToken = nil
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    func onOutcomeChanged() {
        if outcome != "pending", settledAt.trimmingCharacters(in: .whitespaces).isEmpty {
            settledAt = Self.nowLocal()
        }
    }

    private static func displayOutcome(_ bet: Bet) -> String {
        if bet.eachWay, bet.placed, bet.outcome == "loss" { return "placed" }
        return bet.outcome
    }

    private static func nowLocal() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.string(from: Date())
    }

    private static func nowIso() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.string(from: Date())
    }

    private static func parseDateTime(_ text: String, required: Bool) throws -> String? {
        let trimmed = text.trimmingCharacters(in: .whitespaces)
        if trimmed.isEmpty {
            if required { throw NSError(domain: "Bet", code: 1) }
            return nil
        }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        guard let date = formatter.date(from: trimmed) else {
            throw NSError(domain: "Bet", code: 1)
        }
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.string(from: date)
    }

    private static func formatDateTime(_ iso: String?) -> String {
        guard let iso, !iso.isEmpty else { return "" }
        let inFormatter = DateFormatter()
        inFormatter.dateFormat = "yyyy-MM-dd'T'HH:mm"
        let outFormatter = DateFormatter()
        outFormatter.dateFormat = "yyyy-MM-dd HH:mm"
        if let date = inFormatter.date(from: String(iso.prefix(16))) {
            return outFormatter.string(from: date)
        }
        return ""
    }
}

private extension String {
    var nilIfBlank: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

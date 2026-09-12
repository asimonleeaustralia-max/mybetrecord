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
    @Published var saved = false
    @Published var deleted = false
    @Published var sport = "Football"
    @Published var event = ""
    @Published var selection = ""
    @Published var oddsFormat = "decimal"
    @Published var odds = ""
    @Published var stake = ""
    @Published var currency = "GBP"
    @Published var betType = "Win"
    @Published var outcome = "pending"
    @Published var bookmaker = ""
    @Published var portal = ""
    @Published var tipster = ""
    @Published var notes = ""
    @Published var eachWay = false
    @Published var freeBet = false
    @Published var cashOut = ""
    @Published var eventAt = ""
    @Published var closingOdds = ""
    @Published var isMultiple = false
    @Published var legs: [LegInput] = [LegInput(), LegInput()]
    @Published var shareToken: String?
    @Published var sharing = false

    let betId: String?
    let isEdit: Bool
    private let betsRepository: BetsRepository

    init(betId: String?, betsRepository: BetsRepository) {
        self.betId = betId == "new" ? nil : betId
        self.isEdit = betId != nil && betId != "new"
        self.betsRepository = betsRepository
        if let id = self.betId { Task { await load(id: id) } }
    }

    func load(id: String) async {
        loading = true
        defer { loading = false }
        do {
            let bet = try await betsRepository.getBet(id: id)
            sport = bet.sport
            event = bet.event
            selection = bet.selection
            oddsFormat = "decimal"
            odds = String(bet.oddsDecimal)
            stake = String(bet.stake)
            currency = bet.currency
            betType = bet.betType
            outcome = bet.outcome
            bookmaker = bet.bookmaker ?? ""
            portal = bet.portal ?? ""
            tipster = bet.tipster ?? ""
            notes = bet.notes ?? ""
            eachWay = bet.eachWay
            freeBet = bet.freeBet
            cashOut = bet.cashOutAmount.map { String($0) } ?? ""
            eventAt = Self.formatEventAt(bet.eventAt)
            closingOdds = bet.closingOdds.map { String($0) } ?? ""
            isMultiple = bet.isMultiple
            if bet.isMultiple, !bet.legs.isEmpty {
                legs = bet.legs.map { LegInput(event: $0.event, selection: $0.selection, odds: String($0.oddsDecimal)) }
            }
            shareToken = bet.shareToken
        } catch {
            self.errorMessage = error.userMessage
        }
    }

    func save() async {
        guard let stakeValue = Double(stake) else {
            errorMessage = tr("android.requiredFields")
            return
        }
        let eventAtIso: String?
        do {
            eventAtIso = try Self.parseEventAt(eventAt)
        } catch {
            errorMessage = tr("android.invalidEventAt")
            return
        }

        var legsForApi: [BetLegCreate]?
        var oddsPair: (Double, Double?)?
        if isMultiple {
            var parsed: [BetLegCreate] = []
            for leg in legs {
                guard !leg.event.isEmpty, !leg.selection.isEmpty else {
                    errorMessage = tr("form.legMissingFields")
                    return
                }
                guard let legOdds = oddsForApi(leg.odds, format: oddsFormat) else {
                    errorMessage = tr("form.legBadOdds")
                    return
                }
                parsed.append(BetLegCreate(event: leg.event, selection: leg.selection, odds: legOdds.0, oddsFormat: oddsFormat, oddsDenominator: legOdds.1))
            }
            guard parsed.count >= 2 else {
                errorMessage = tr("form.needTwoLegs")
                return
            }
            legsForApi = parsed
        } else {
            guard !event.isEmpty, !selection.isEmpty, let pair = oddsForApi(odds, format: oddsFormat) else {
                errorMessage = oddsFormat == "fractional" && BetMath.parseFractional(odds) == nil ? tr("android.invalidFractional") : tr("android.requiredFields")
                return
            }
            oddsPair = pair
        }

        saving = true
        errorMessage = nil
        defer { saving = false }
        do {
            if let betId {
                let update = BetUpdate(
                    sport: sport.trimmingCharacters(in: .whitespaces),
                    event: event.nilIfBlank,
                    selection: selection.nilIfBlank,
                    odds: oddsPair?.0,
                    stake: stakeValue,
                    betType: betType,
                    currency: currency.uppercased(),
                    oddsFormat: oddsFormat,
                    oddsDenominator: oddsPair?.1,
                    outcome: outcome,
                    bookmaker: bookmaker.nilIfBlank,
                    portal: portal.nilIfBlank,
                    tipster: tipster.nilIfBlank,
                    notes: notes.nilIfBlank,
                    eachWay: !isMultiple && eachWay,
                    freeBet: !isMultiple && freeBet,
                    isMultiple: isMultiple,
                    legs: legsForApi,
                    cashOutAmount: Double(cashOut),
                    closingOdds: Double(closingOdds),
                    eventAt: eventAtIso
                )
                _ = try await betsRepository.updateBet(id: betId, body: update)
            } else {
                let create = BetCreate(
                    sport: sport.trimmingCharacters(in: .whitespaces),
                    event: event.nilIfBlank,
                    selection: selection.nilIfBlank,
                    odds: oddsPair?.0,
                    stake: stakeValue,
                    betType: betType,
                    side: "back",
                    currency: currency.uppercased(),
                    oddsFormat: oddsFormat,
                    oddsDenominator: oddsPair?.1,
                    outcome: outcome,
                    tournament: nil,
                    bookmaker: bookmaker.nilIfBlank,
                    portal: portal.nilIfBlank,
                    tipster: tipster.nilIfBlank,
                    notes: notes.nilIfBlank,
                    eachWay: !isMultiple && eachWay,
                    placed: false,
                    freeBet: !isMultiple && freeBet,
                    isMultiple: isMultiple,
                    legs: legsForApi,
                    cashOutAmount: Double(cashOut),
                    closingOdds: Double(closingOdds),
                    placedAt: nil,
                    eventAt: eventAtIso
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

    func currentDecimalOdds() -> Double? {
        if isMultiple {
            let values = legs.compactMap { parseOddsToDecimal($0.odds, format: oddsFormat) }
            return BetMath.combinedOdds(values)
        }
        return parseOddsToDecimal(odds, format: oddsFormat)
    }

    private func parseOddsToDecimal(_ text: String, format: String) -> Double? {
        guard !text.isEmpty else { return nil }
        if format == "fractional" {
            guard let (n, d) = BetMath.parseFractional(text) else { return nil }
            return BetMath.fractionalToDecimal(numerator: n, denominator: d)
        }
        guard let value = Double(text), value > 1 else { return nil }
        return value
    }

    private func oddsForApi(_ text: String, format: String) -> (Double, Double?)? {
        if format == "fractional" {
            guard let (n, d) = BetMath.parseFractional(text) else { return nil }
            return (n, d)
        }
        guard let value = Double(text), value > 1 else { return nil }
        return (value, nil)
    }

    private static func parseEventAt(_ text: String) throws -> String? {
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return nil }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        guard let date = formatter.date(from: text.trimmingCharacters(in: .whitespaces)) else {
            throw NSError(domain: "Bet", code: 1)
        }
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.string(from: date)
    }

    private static func formatEventAt(_ iso: String?) -> String {
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

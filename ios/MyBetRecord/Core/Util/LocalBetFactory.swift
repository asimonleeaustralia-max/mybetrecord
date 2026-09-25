import Foundation

enum LocalBetFactory {
    static func localId() -> String {
        "local_\(UUID().uuidString)"
    }

    static func isLocalId(_ id: String) -> Bool {
        id.hasPrefix("local_")
    }

    static func make(from body: BetCreate, id: String) -> Bet {
        let placedAt = body.placedAt ?? isoNow()
        let (event, selection, oddsDecimal, legs) = resolveOdds(body)
        let profit = BetMath.settleProfit(
            stake: body.stake,
            oddsDecimal: oddsDecimal,
            outcome: body.outcome,
            eachWay: body.eachWay,
            placeFraction: body.placeFraction ?? 0.25,
            side: body.side,
            freeBet: body.freeBet,
            exchangeCommissionPct: body.exchangeCommissionPct ?? 0,
            cashOutAmount: body.cashOutAmount
        ) ?? 0
        let personalEdge = body.personalImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: oddsDecimal, impliedDecimal: $0) }
        let modelEdge = body.modelImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: oddsDecimal, impliedDecimal: $0) }
        let tipsterEdge = body.tipsterImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: oddsDecimal, impliedDecimal: $0) }
        let clv = body.closingOdds.flatMap { BetMath.clvPct(takenDecimal: oddsDecimal, closingDecimal: $0) }

        return Bet(
            id: id,
            tournament: body.tournament,
            event: event,
            selection: selection,
            sport: body.sport,
            betType: body.betType,
            side: body.side,
            isMultiple: body.isMultiple,
            legs: legs,
            placedAt: placedAt,
            eventAt: body.eventAt,
            settledAt: body.settledAt,
            oddsDecimal: oddsDecimal,
            oddsFormat: body.oddsFormat,
            stake: body.stake,
            currency: body.currency,
            eachWay: body.eachWay,
            placeFraction: body.placeFraction ?? 0.25,
            placed: body.placed,
            freeBet: body.freeBet,
            outcome: body.outcome,
            profit: profit,
            cashOutAmount: body.cashOutAmount,
            betModel: body.betModel,
            modelImpliedOdds: body.modelImpliedOdds,
            personalImpliedOdds: body.personalImpliedOdds,
            tipsterImpliedOdds: body.tipsterImpliedOdds,
            personalEdgePct: personalEdge,
            modelEdgePct: modelEdge,
            tipsterEdgePct: tipsterEdge,
            kellyStake: nil,
            modelKellyStake: nil,
            bookmaker: body.bookmaker,
            portal: body.portal,
            exchangeCommissionPct: body.exchangeCommissionPct,
            tipster: body.tipster,
            betBroker: body.betBroker,
            notes: body.notes,
            closingOdds: body.closingOdds,
            closingOddsExchange: body.closingOddsExchange,
            clvPct: clv,
            edgePct: personalEdge,
            shareToken: nil,
            createdAt: isoNow(),
            updatedAt: isoNow()
        )
    }

    static func apply(update: BetUpdate, to bet: Bet) -> Bet {
        var next = bet
        if let v = update.sport { next.sport = v }
        if let v = update.event { next.event = v }
        if let v = update.selection { next.selection = v }
        if let v = update.stake { next.stake = v }
        if let v = update.betType { next.betType = v }
        if let v = update.side { next.side = v }
        if let v = update.currency { next.currency = v }
        if let v = update.oddsFormat { next.oddsFormat = v }
        if let v = update.outcome { next.outcome = v }
        if let v = update.tournament { next.tournament = v }
        if let v = update.bookmaker { next.bookmaker = v }
        if let v = update.portal { next.portal = v }
        if let v = update.exchangeCommissionPct { next.exchangeCommissionPct = v }
        if let v = update.tipster { next.tipster = v }
        if let v = update.betBroker { next.betBroker = v }
        if let v = update.notes { next.notes = v }
        if let v = update.eachWay { next.eachWay = v }
        if let v = update.placeFraction { next.placeFraction = v }
        if let v = update.placed { next.placed = v }
        if let v = update.freeBet { next.freeBet = v }
        if let v = update.isMultiple { next.isMultiple = v }
        if let v = update.cashOutAmount { next.cashOutAmount = v }
        if let v = update.betModel { next.betModel = v }
        if let v = update.modelImpliedOdds { next.modelImpliedOdds = v }
        if let v = update.personalImpliedOdds { next.personalImpliedOdds = v }
        if let v = update.tipsterImpliedOdds { next.tipsterImpliedOdds = v }
        if let v = update.closingOdds { next.closingOdds = v }
        if let v = update.closingOddsExchange { next.closingOddsExchange = v }
        if let v = update.eventAt { next.eventAt = v }
        if let v = update.placedAt { next.placedAt = v }
        if let v = update.settledAt { next.settledAt = v }

        if next.isMultiple, let legs = update.legs {
            let fmt = update.oddsFormat ?? next.oddsFormat
            next.legs = legs.enumerated().compactMap { index, leg in
                guard let dec = decimalOdds(value: leg.odds, format: leg.oddsFormat ?? fmt, denominator: leg.oddsDenominator) else {
                    return nil
                }
                return BetLeg(
                    legIndex: index,
                    event: leg.event,
                    selection: leg.selection,
                    oddsDecimal: dec,
                    oddsFormat: leg.oddsFormat ?? fmt
                )
            }
            if let combined = BetMath.combinedOdds(next.legs.map(\.oddsDecimal)) {
                next.oddsDecimal = combined
            }
            next.event = next.legs.map(\.event).joined(separator: " / ")
            next.selection = next.legs.map(\.selection).joined(separator: " / ")
        } else if let odds = update.odds {
            let fmt = update.oddsFormat ?? next.oddsFormat
            if let dec = decimalOdds(value: odds, format: fmt, denominator: update.oddsDenominator) {
                next.oddsDecimal = dec
            }
            next.legs = []
        }

        next.profit = BetMath.settleProfit(
            stake: next.stake,
            oddsDecimal: next.oddsDecimal,
            outcome: next.outcome,
            eachWay: next.eachWay,
            placeFraction: next.placeFraction,
            side: next.side,
            freeBet: next.freeBet,
            exchangeCommissionPct: next.exchangeCommissionPct ?? 0,
            cashOutAmount: next.cashOutAmount
        ) ?? next.profit
        next.personalEdgePct = next.personalImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: next.oddsDecimal, impliedDecimal: $0) }
        next.modelEdgePct = next.modelImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: next.oddsDecimal, impliedDecimal: $0) }
        next.tipsterEdgePct = next.tipsterImpliedOdds.flatMap { BetMath.edgePct(oddsDecimal: next.oddsDecimal, impliedDecimal: $0) }
        next.clvPct = next.closingOdds.flatMap { BetMath.clvPct(takenDecimal: next.oddsDecimal, closingDecimal: $0) }
        next.edgePct = next.personalEdgePct
        next.updatedAt = isoNow()
        return next
    }

    static func withId(_ bet: Bet, id: String) -> Bet {
        Bet(
            id: id,
            tournament: bet.tournament,
            event: bet.event,
            selection: bet.selection,
            sport: bet.sport,
            betType: bet.betType,
            side: bet.side,
            isMultiple: bet.isMultiple,
            legs: bet.legs,
            placedAt: bet.placedAt,
            eventAt: bet.eventAt,
            settledAt: bet.settledAt,
            oddsDecimal: bet.oddsDecimal,
            oddsFormat: bet.oddsFormat,
            stake: bet.stake,
            currency: bet.currency,
            eachWay: bet.eachWay,
            placeFraction: bet.placeFraction,
            placed: bet.placed,
            freeBet: bet.freeBet,
            outcome: bet.outcome,
            profit: bet.profit,
            cashOutAmount: bet.cashOutAmount,
            betModel: bet.betModel,
            modelImpliedOdds: bet.modelImpliedOdds,
            personalImpliedOdds: bet.personalImpliedOdds,
            tipsterImpliedOdds: bet.tipsterImpliedOdds,
            personalEdgePct: bet.personalEdgePct,
            modelEdgePct: bet.modelEdgePct,
            tipsterEdgePct: bet.tipsterEdgePct,
            kellyStake: bet.kellyStake,
            modelKellyStake: bet.modelKellyStake,
            bookmaker: bet.bookmaker,
            portal: bet.portal,
            exchangeCommissionPct: bet.exchangeCommissionPct,
            tipster: bet.tipster,
            betBroker: bet.betBroker,
            notes: bet.notes,
            closingOdds: bet.closingOdds,
            closingOddsExchange: bet.closingOddsExchange,
            clvPct: bet.clvPct,
            edgePct: bet.edgePct,
            shareToken: bet.shareToken,
            createdAt: bet.createdAt,
            updatedAt: bet.updatedAt
        )
    }

    /// Approximate dashboard metrics from the local cache when the API is unreachable.
    static func summary(from bets: [Bet]) -> ReportSummary {
        var turnover = 0.0
        var profit = 0.0
        var settled = 0
        var wins = 0
        var losses = 0
        var voids = 0
        let currency = bets.map(\.currency).mostCommon() ?? bets.first?.currency

        for bet in bets {
            let hasCashOut = bet.cashOutAmount != nil
            if bet.outcome == "pending", !hasCashOut { continue }
            settled += 1
            profit += bet.profit
            if bet.freeBet {
                // free-bet turnover is typically 0 for stake return purposes; keep simple
            } else if bet.side == "lay", bet.oddsDecimal > 1 {
                turnover += bet.stake * (bet.oddsDecimal - 1)
            } else {
                turnover += bet.stake
            }
            if hasCashOut {
                if bet.profit > 0 { wins += 1 }
                else if bet.profit < 0 { losses += 1 }
                else if bet.outcome == "void" { voids += 1 }
            } else if bet.outcome == "void" {
                voids += 1
            } else if ["win", "half_win", "placed"].contains(bet.outcome), bet.profit > 0 {
                wins += 1
            } else if bet.profit < 0 {
                losses += 1
            }
        }

        let yieldPct = turnover > 0 ? profit / turnover * 100 : 0
        return ReportSummary(
            turnover: (turnover * 100).rounded() / 100,
            profit: (profit * 100).rounded() / 100,
            yieldPct: (yieldPct * 100).rounded() / 100,
            roiPct: (yieldPct * 100).rounded() / 100,
            strikeRatePct: settled > 0 ? (Double(wins) / Double(settled) * 10000).rounded() / 100 : 0,
            settledBets: settled,
            wins: wins,
            losses: losses,
            voids: voids,
            bankroll: nil,
            roiVsBankrollPct: nil,
            baseCurrency: currency,
            currency: currency,
            totalBets: bets.count
        )
    }

    private static func resolveOdds(_ body: BetCreate) -> (String, String, Double, [BetLeg]) {
        if body.isMultiple, let createLegs = body.legs, createLegs.count >= 2 {
            let fmt = body.oddsFormat
            let legs: [BetLeg] = createLegs.enumerated().compactMap { index, leg in
                guard let dec = decimalOdds(
                    value: leg.odds,
                    format: leg.oddsFormat ?? fmt,
                    denominator: leg.oddsDenominator
                ) else { return nil }
                return BetLeg(
                    legIndex: index,
                    event: leg.event,
                    selection: leg.selection,
                    oddsDecimal: dec,
                    oddsFormat: leg.oddsFormat ?? fmt
                )
            }
            let combined = BetMath.combinedOdds(legs.map(\.oddsDecimal)) ?? 0
            let event = legs.map(\.event).joined(separator: " / ")
            let selection = legs.map(\.selection).joined(separator: " / ")
            return (event, selection, combined, legs)
        }

        let oddsValue = body.odds ?? 0
        let dec = decimalOdds(value: oddsValue, format: body.oddsFormat, denominator: body.oddsDenominator) ?? max(oddsValue, 0)
        return (body.event ?? "", body.selection ?? "", dec, [])
    }

    private static func decimalOdds(value: Double, format: String, denominator: Double?) -> Double? {
        if format == "fractional", let den = denominator, den > 0, value > 0 {
            return BetMath.fractionalToDecimal(numerator: value, denominator: den)
        }
        // American / Asian signed formats need the sign preserved as text.
        let text: String
        if ["american", "malaysian", "indonesian"].contains(format), value > 0 {
            text = "+\(value)"
        } else {
            text = String(value)
        }
        return BetMath.toDecimal(text, format: format, denominator: denominator)
    }

    private static func isoNow() -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone.current
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return formatter.string(from: Date())
    }
}

private extension Array where Element == String {
    func mostCommon() -> String? {
        guard !isEmpty else { return nil }
        var counts: [String: Int] = [:]
        for value in self { counts[value, default: 0] += 1 }
        return counts.max(by: { $0.value < $1.value })?.key
    }
}

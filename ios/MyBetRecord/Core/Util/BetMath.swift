import Foundation

/// Client-side betting maths, ported from the web app and shared Python module.
/// The backend remains the source of truth for stored profit / edge values.
enum BetMath {
    static let oddsFormats = ["decimal", "american", "fractional", "hong_kong", "malaysian", "indonesian"]

    static func parseFractional(_ text: String) -> (numerator: Double, denominator: Double)? {
        let parts = text.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: "/")
        guard let num = Double(parts.first?.trimmingCharacters(in: .whitespaces) ?? "") else { return nil }
        let den: Double
        if parts.count == 1 {
            den = 1
        } else if parts.count == 2, let d = Double(parts[1].trimmingCharacters(in: .whitespaces)) {
            den = d
        } else {
            return nil
        }
        guard num > 0, den > 0 else { return nil }
        return (num, den)
    }

    static func fractionalToDecimal(numerator: Double, denominator: Double) -> Double {
        1 + numerator / denominator
    }

    static func parseSigned(_ text: String) -> Double? {
        var raw = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if raw.hasPrefix("+") { raw.removeFirst() }
        guard !raw.isEmpty, let value = Double(raw), value != 0 else { return nil }
        return value
    }

    /// Normalise any supported odds input to decimal odds (> 1), or nil when invalid.
    static func toDecimal(_ text: String, format: String, denominator: Double? = nil) -> Double? {
        let raw = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return nil }
        switch format {
        case "decimal":
            guard let value = Double(raw), value > 1 else { return nil }
            return value
        case "american":
            guard let a = parseSigned(raw) else { return nil }
            return a > 0 ? 1 + a / 100 : 1 + 100 / abs(a)
        case "fractional":
            if let den = denominator {
                guard let num = Double(raw), num > 0, den > 0 else { return nil }
                return fractionalToDecimal(numerator: num, denominator: den)
            }
            guard let (n, d) = parseFractional(raw) else { return nil }
            return fractionalToDecimal(numerator: n, denominator: d)
        case "hong_kong":
            guard let hk = Double(raw), hk >= 0 else { return nil }
            let d = 1 + hk
            return d > 1 ? d : nil
        case "malaysian", "indonesian":
            guard let o = parseSigned(raw) else { return nil }
            let d = o > 0 ? 1 + o : 1 + 1 / abs(o)
            return d > 1 ? d : nil
        default:
            guard let value = Double(raw), value > 1 else { return nil }
            return value
        }
    }

    /// Odds payload for the API: (odds value, optional fractional denominator).
    static func oddsForApi(_ text: String, format: String) -> (odds: Double, denominator: Double?)? {
        let raw = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return nil }
        guard toDecimal(raw, format: format) != nil else { return nil }
        if format == "fractional" {
            guard let (n, d) = parseFractional(raw) else { return nil }
            return (n, d)
        }
        if format == "american" || format == "malaysian" || format == "indonesian" {
            guard let value = parseSigned(raw) else { return nil }
            return (value, nil)
        }
        guard let value = Double(raw) else { return nil }
        return (value, nil)
    }

    /// Format a decimal price back into the chosen display format (e.g. when editing).
    static func formatFromDecimal(_ decimal: Double, format: String) -> String {
        guard decimal > 1 else { return "" }
        switch format {
        case "american":
            if decimal >= 2 {
                let a = Int(((decimal - 1) * 100).rounded())
                return "+\(a)"
            }
            let a = Int((-100 / (decimal - 1)).rounded())
            return "\(a)"
        case "fractional":
            let parts = decimalToFractionalParts(decimal)
            return "\(Int(parts.numerator))/\(Int(parts.denominator))"
        case "hong_kong":
            return String(format: "%.2f", ((decimal - 1) * 10000).rounded() / 10000)
        case "malaysian":
            return formatSignedAsian(decimal, positiveWhenUnderEvens: true)
        case "indonesian":
            return formatSignedAsian(decimal, positiveWhenUnderEvens: false)
        default:
            return String(format: "%.2f", decimal)
        }
    }

    static func effectiveDecimalOdds(oddsDecimal: Double, commissionPct: Double) -> Double? {
        guard oddsDecimal > 1, commissionPct > 0 else { return nil }
        return ((1 + (oddsDecimal - 1) * (1 - commissionPct / 100)) * 10000).rounded() / 10000
    }

    static func layLiability(backersStake: Double, oddsDecimal: Double) -> Double? {
        guard backersStake > 0, oddsDecimal > 1 else { return nil }
        return (backersStake * (oddsDecimal - 1) * 100).rounded() / 100
    }

    static func edgePct(oddsDecimal: Double, impliedDecimal: Double) -> Double? {
        guard oddsDecimal > 1, impliedDecimal > 1 else { return nil }
        let p = 1 / impliedDecimal
        return (p * (oddsDecimal - 1) - (1 - p)) * 100
    }

    struct KellyResult {
        let fraction: Double
        let stake: Double
    }

    static func kelly(oddsDecimal: Double, impliedDecimal: Double, bankroll: Double, multiplier: Double = 1) -> KellyResult? {
        guard oddsDecimal > 1, impliedDecimal > 1, bankroll > 0 else { return nil }
        let b = oddsDecimal - 1
        let p = 1 / impliedDecimal
        let q = 1 - p
        let m = multiplier > 0 ? multiplier : 1
        let f = max(0, (b * p - q) / b) * m
        return KellyResult(fraction: f, stake: f * bankroll)
    }

    static func combinedOdds(_ legOdds: [Double]) -> Double? {
        guard legOdds.count >= 2, legOdds.allSatisfy({ $0 > 1 }) else { return nil }
        return legOdds.reduce(1, *)
    }

    static func clvPct(takenDecimal: Double, closingDecimal: Double) -> Double? {
        guard takenDecimal > 1, closingDecimal > 1 else { return nil }
        return ((takenDecimal / closingDecimal - 1) * 10000).rounded() / 100
    }

    static func maxCashOutReturn(stake: Double, oddsDecimal: Double, freeBet: Bool) -> Double? {
        guard stake > 0, oddsDecimal > 1 else { return nil }
        let value = freeBet ? stake * (oddsDecimal - 1) : stake * oddsDecimal
        return (value * 100).rounded() / 100
    }

    /// Mirror of `betting_math.settle_profit` / web `computeSettlementProfit`.
    static func settleProfit(
        stake: Double,
        oddsDecimal: Double,
        outcome: String,
        eachWay: Bool = false,
        placeFraction: Double = 0.25,
        side: String = "back",
        freeBet: Bool = false,
        exchangeCommissionPct: Double = 0,
        cashOutAmount: Double? = nil
    ) -> Double? {
        guard stake > 0 else { return nil }

        if let cashOut = cashOutAmount {
            return ((freeBet ? cashOut : cashOut - stake) * 100).rounded() / 100
        }

        let outcome = outcome.lowercased()
        if outcome == "pending" || outcome == "void" { return 0 }
        guard oddsDecimal > 1 else { return 0 }

        let isLay = side.lowercased() == "lay"
        var gross: Double = 0

        if isLay {
            if outcome == "win" {
                gross = stake
            } else if outcome == "loss" {
                gross = -(layLiability(backersStake: stake, oddsDecimal: oddsDecimal) ?? 0)
            }
        } else if !eachWay {
            switch outcome {
            case "win":
                gross = stake * (oddsDecimal - 1)
            case "half_win":
                gross = 0.5 * stake * (oddsDecimal - 1)
            case "half_loss":
                gross = freeBet ? 0 : -0.5 * stake
            case "loss":
                gross = freeBet ? 0 : -stake
            default:
                gross = 0
            }
        } else {
            let unit = stake / 2
            let placeOdds = 1 + (oddsDecimal - 1) * placeFraction
            if outcome == "win" {
                gross = unit * (oddsDecimal - 1) + unit * (placeOdds - 1)
            } else if outcome == "placed" {
                gross = (freeBet ? 0 : -unit) + unit * (placeOdds - 1)
            } else {
                gross = freeBet ? 0 : -stake
            }
        }

        if gross > 0, exchangeCommissionPct != 0 {
            gross -= gross * (exchangeCommissionPct / 100)
        }
        return (gross * 100).rounded() / 100
    }

    // MARK: - Private helpers

    private static func formatSignedAsian(_ decimal: Double, positiveWhenUnderEvens: Bool) -> String {
        let o: Double
        if positiveWhenUnderEvens {
            o = decimal <= 2 ? decimal - 1 : -1 / (decimal - 1)
        } else {
            o = decimal >= 2 ? decimal - 1 : -1 / (decimal - 1)
        }
        let rounded = (o * 10000).rounded() / 10000
        let body = String(format: "%g", abs(rounded))
        return rounded > 0 ? "+\(body)" : "-\(body)"
    }

    private static func decimalToFractionalParts(_ decimal: Double, maxDen: Int = 100) -> (numerator: Double, denominator: Double) {
        let x = decimal - 1
        var bestNum = 1.0, bestDen = 1.0, bestErr = abs(x - 1)
        for den in 1...maxDen {
            let num = (x * Double(den)).rounded()
            let err = abs(x - num / Double(den))
            if err < bestErr {
                bestErr = err
                bestNum = num
                bestDen = Double(den)
            }
        }
        let g = gcd(Int(bestNum.rounded()), Int(bestDen.rounded()))
        return (bestNum / Double(g), bestDen / Double(g))
    }

    private static func gcd(_ a: Int, _ b: Int) -> Int {
        var a = abs(a), b = abs(b)
        while b != 0 {
            let t = b
            b = a % b
            a = t
        }
        return a == 0 ? 1 : a
    }
}

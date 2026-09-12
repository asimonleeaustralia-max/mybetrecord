import Foundation

/// Client-side betting maths, ported from the web app and Android client.
enum BetMath {
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
}

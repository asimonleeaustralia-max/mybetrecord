import SwiftUI

struct ToolsView: View {
    @EnvironmentObject private var auth: AuthRepository
    @EnvironmentObject private var environment: AppEnvironment
    @State private var user: User?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(tr("android.tools")).font(.title2)
                Text(tr("android.toolsSub")).font(.footnote).foregroundStyle(.secondary)
                KellyCalculatorCard(
                    defaultBankroll: user?.bankroll ?? 0,
                    defaultMultiplier: user?.kellyMultiplier ?? 1,
                    currency: user?.baseCurrency ?? "GBP"
                )
                LiabilityCalculatorCard(currency: user?.baseCurrency ?? "GBP")
            }
            .padding()
        }
        .task {
            user = try? await auth.me()
        }
    }
}

private struct KellyCalculatorCard: View {
    let defaultBankroll: Double
    let defaultMultiplier: Double
    let currency: String
    @State private var odds = ""
    @State private var implied = ""
    @State private var bankroll = ""
    @State private var multiplier = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(tr("android.kellyTitle")).font(.headline)
            AppTextField(title: tr("android.kellyOdds"), text: $odds, keyboard: .decimalPad)
            AppTextField(title: tr("android.kellyImplied"), text: $implied, keyboard: .decimalPad)
            AppTextField(title: tr("settings.bankroll"), text: $bankroll, keyboard: .decimalPad)
            AppTextField(title: tr("settings.kellyMultiplier"), text: $multiplier, keyboard: .decimalPad)
            if let o = Double(odds), let i = Double(implied), let edge = BetMath.edgePct(oddsDecimal: o, impliedDecimal: i) {
                Text("\(tr("form.personalEdge")): \(tr("form.edgeValue", params: ["pct": String(format: "%.2f", edge)]))")
            }
            if let o = Double(odds), let i = Double(implied), let b = Double(bankroll), b > 0 {
                let m = Double(multiplier) ?? 1
                if let kelly = BetMath.kelly(oddsDecimal: o, impliedDecimal: i, bankroll: b, multiplier: m), kelly.fraction > 0 {
                    Text(tr("form.kellySuggest", params: [
                        "stake": String(format: "%.2f", kelly.stake),
                        "currency": currency,
                        "pct": String(format: "%.1f", kelly.fraction * 100),
                    ])).font(.headline)
                } else {
                    Text(tr("form.kellyNoEdge"))
                }
            }
        }
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
        .onAppear {
            if defaultBankroll > 0 { bankroll = String(defaultBankroll) }
            multiplier = String(defaultMultiplier)
        }
    }
}

private struct LiabilityCalculatorCard: View {
    let currency: String
    @State private var stake = ""
    @State private var odds = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(tr("android.liabilityTitle")).font(.headline)
            AppTextField(title: tr("form.backersStake"), text: $stake, keyboard: .decimalPad)
            AppTextField(title: tr("android.layOdds"), text: $odds, keyboard: .decimalPad)
            if let s = Double(stake), let o = Double(odds), let liability = BetMath.layLiability(backersStake: s, oddsDecimal: o) {
                Text("\(tr("form.liability")): \(Formatters.money(liability, currency: currency))").font(.headline)
                Text(tr("form.backersStakeHint")).font(.footnote).foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }
}

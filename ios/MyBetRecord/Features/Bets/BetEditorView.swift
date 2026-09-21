import SwiftUI
import UIKit

struct BetEditorView: View {
    @EnvironmentObject private var environment: AppEnvironment
    let betId: String
    let onDone: () -> Void

    @State private var model: BetEditorModel?
    @State private var showShare = false

    var body: some View {
        Group {
            if let model {
                BetEditorForm(model: model, onDone: onDone, showShare: $showShare)
            } else {
                LoadingView()
            }
        }
        .onAppear {
            if model == nil {
                model = BetEditorModel(
                    betId: betId,
                    betsRepository: environment.betsRepository,
                    authRepository: environment.authRepository
                )
            }
        }
        .sheet(isPresented: $showShare) {
            if let token = model?.shareToken {
                ShareSheet(items: [Formatters.shareLinkURL(token: token)])
            }
        }
    }
}

private struct BetEditorForm: View {
    @ObservedObject var model: BetEditorModel
    let onDone: () -> Void
    @Binding var showShare: Bool

    private let portals: [(String, String)] = [
        ("", "form.optional"),
        ("online", "form.portalOnline"),
        ("phone", "form.portalPhone"),
        ("in_shop", "form.portalInShop"),
    ]

    var body: some View {
        Group {
            if model.loading { LoadingView() }
            else { editorForm }
        }
        .navigationTitle(model.isEdit ? tr("form.editTitle") : tr("form.recordTitle"))
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: model.saved) { saved in if saved { onDone() } }
        .onChange(of: model.deleted) { deleted in if deleted { onDone() } }
    }

    private var editorForm: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let error = model.errorMessage { ErrorText(message: error) }
                if let warning = model.warningMessage {
                    Text(warning).foregroundStyle(.orange).font(.callout)
                }

                sectionHeader(model.isLay ? tr("form.whatYouLay") : tr("form.whatYouBacked"))

                AppTextField(title: tr("form.sport"), text: $model.sport)
                AppTextField(title: tr("form.betType"), text: $model.betType)

                if !model.isEdit || model.isMultiple {
                    Toggle(isOn: Binding(
                        get: { model.isMultiple },
                        set: { model.setMultiple($0) }
                    )) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(tr("form.multiple"))
                            Text(tr("form.multipleHint")).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .disabled(model.isEdit)
                }

                if !model.isMultiple {
                    ChoicePicker(
                        label: tr("form.side"),
                        options: [("back", tr("form.sideBack")), ("lay", tr("form.sideLay"))],
                        selection: Binding(get: { model.side }, set: { model.setSide($0) })
                    )
                }

                AppTextField(title: tr("form.tournament"), text: $model.tournament)
                AppTextField(title: tr("form.bookmaker"), text: $model.bookmaker)
                ChoicePicker(
                    label: tr("form.portal"),
                    options: portals.map { ($0.0, tr($0.1)) },
                    selection: $model.portal
                )
                AppTextField(title: tr("form.commission"), text: $model.exchangeCommission, keyboard: .decimalPad)
                Text(tr("form.commissionHint")).font(.caption).foregroundStyle(.secondary)

                if !model.isMultiple {
                    AppTextField(title: tr("form.event"), text: $model.event)
                    AppTextField(title: tr("form.selection"), text: $model.selection)
                }

                AppTextField(title: "\(tr("form.eventAt")) — \(tr("form.dateHint"))", text: $model.eventAt)
                AppTextField(title: "\(tr("form.placedAt")) — \(tr("form.dateHint"))", text: $model.placedAt)

                sectionHeader(tr("form.oddsStake"))

                ChoicePicker(
                    label: tr("form.oddsFormat"),
                    options: BetMath.oddsFormats.map { ($0, oddsFormatLabel($0)) },
                    selection: Binding(get: { model.oddsFormat }, set: { model.setOddsFormat($0) })
                )

                if model.isMultiple {
                    Text(tr("form.selections")).font(.headline)
                    Text(tr("form.legsHint")).font(.caption).foregroundStyle(.secondary)
                    ForEach(Array(model.legs.indices), id: \.self) { index in
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(tr("form.legLabel", params: ["n": "\(index + 1)"]))
                                    .font(.subheadline.weight(.semibold))
                                Spacer()
                                if model.legs.count > 2 {
                                    Button(role: .destructive) {
                                        model.removeLeg(at: index)
                                    } label: {
                                        Image(systemName: "trash")
                                    }
                                }
                            }
                            AppTextField(title: tr("form.event"), text: $model.legs[index].event)
                            AppTextField(title: tr("form.selection"), text: $model.legs[index].selection)
                            AppTextField(
                                title: oddsFieldTitle,
                                text: $model.legs[index].odds,
                                keyboard: oddsKeyboard
                            )
                        }
                        .padding()
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
                    }
                    Button(tr("form.addSelection")) { model.addLeg() }
                        .disabled(model.legs.count >= 10)
                    if let combined = model.currentDecimalOdds() {
                        Text("\(tr("form.combinedOdds")): \(String(format: "%.2f", combined))")
                            .font(.subheadline.weight(.medium))
                    }
                } else {
                    AppTextField(title: oddsFieldTitle, text: $model.odds, keyboard: oddsKeyboard)
                    if model.oddsFormat == "fractional",
                       let (n, d) = BetMath.parseFractional(model.odds) {
                        Text("\(tr("form.effectiveOdds")): \(String(format: "%.2f", BetMath.fractionalToDecimal(numerator: n, denominator: d)))")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    if let effective = model.effectiveOddsPreview() {
                        Text("\(tr("form.effectiveOdds")): \(String(format: "%.2f", effective))")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                AppTextField(
                    title: model.isLay ? tr("form.backersStake") : tr("form.stake"),
                    text: $model.stake,
                    keyboard: .decimalPad
                )
                if model.isLay {
                    Text(tr("form.backersStakeHint")).font(.caption).foregroundStyle(.secondary)
                    if let liability = model.liabilityPreview() {
                        Text("\(tr("form.liability")): \(Formatters.money(liability, currency: model.currency))")
                            .font(.subheadline.weight(.medium))
                    }
                }
                AppTextField(title: tr("form.currency"), text: $model.currency)

                if model.canUsePromotions {
                    Toggle(tr("form.eachWay"), isOn: Binding(
                        get: { model.eachWay },
                        set: { model.setEachWay($0) }
                    ))
                    if model.eachWay {
                        Text(tr("form.eachWayNote")).font(.caption).foregroundStyle(.secondary)
                        AppTextField(title: tr("form.placeFraction"), text: $model.placeFraction, keyboard: .decimalPad)
                    }
                    Toggle(tr("form.freeBet"), isOn: $model.freeBet)
                    if model.freeBet {
                        Text(tr("form.freeBetNote")).font(.caption).foregroundStyle(.secondary)
                    }
                }

                sectionHeader(tr("form.settlement"))
                ChoicePicker(
                    label: tr("form.result"),
                    options: model.availableOutcomes.map { ($0, tr("outcomes.\($0)")) },
                    selection: Binding(
                        get: { model.outcome },
                        set: {
                            model.outcome = $0
                            model.onOutcomeChanged()
                        }
                    )
                )
                AppTextField(title: "\(tr("form.settledAt")) — \(tr("form.dateHint"))", text: $model.settledAt)
                AppTextField(
                    title: "\(tr("form.cashOut")) (\(tr("form.cashOutHint")))",
                    text: $model.cashOut,
                    keyboard: .decimalPad
                )
                if let profit = model.settlementProfitPreview() {
                    Text("\(tr("form.settlementProfit")): \(Formatters.money(profit, currency: model.currency))")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(profit >= 0 ? Color.green : Color.red)
                }

                sectionHeader(tr("form.modelling"))
                AppTextField(title: tr("form.betModel"), text: $model.betModel)
                AppTextField(title: tr("form.closingBookmaker"), text: $model.closingOdds, keyboard: .decimalPad)
                AppTextField(title: tr("form.closingExchange"), text: $model.closingOddsExchange, keyboard: .decimalPad)
                if let clv = model.computedClv() {
                    Text("\(tr("bets.clv")): \(String(format: "%.2f", clv))%")
                        .font(.subheadline)
                }
                AppTextField(title: tr("form.personalImplied"), text: $model.personalImpliedOdds, keyboard: .decimalPad)
                edgeRow(label: tr("form.personalEdge"), edge: model.personalEdge(), kelly: model.personalKelly())
                AppTextField(title: tr("form.modelImplied"), text: $model.modelImpliedOdds, keyboard: .decimalPad)
                edgeRow(label: tr("form.modelEdge"), edge: model.modelEdge(), kelly: model.modelKelly())
                AppTextField(title: tr("form.tipsterImplied"), text: $model.tipsterImpliedOdds, keyboard: .decimalPad)
                if let tipsterEdge = model.tipsterEdge() {
                    Text("\(tr("form.tipsterEdge")): \(String(format: "%.2f", tipsterEdge))%")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                sectionHeader(tr("form.notes"))
                AppTextField(title: tr("form.tipster"), text: $model.tipster)
                AppTextField(title: tr("form.betBroker"), text: $model.betBroker)
                AppTextField(title: tr("form.notes"), text: $model.notes, axis: .vertical)

                Button(model.isEdit ? tr("form.saveChanges") : tr("form.saveBet")) {
                    Task { await model.save() }
                }
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
                .disabled(model.saving)

                if model.isEdit {
                    Text(tr("share.shareSection")).font(.headline)
                    Text(tr("share.shareHint")).font(.caption).foregroundStyle(.secondary)
                    if model.shareToken == nil {
                        Button(tr("share.shareBet")) { Task { await model.createShareLink() } }
                            .disabled(model.sharing)
                    } else {
                        Button(tr("share.copyLink")) { showShare = true }
                        Button(tr("share.revokeLink"), role: .destructive) {
                            Task { await model.revokeShareLink() }
                        }
                        .disabled(model.sharing)
                    }
                    Button(tr("bets.deleteAria", params: ["name": model.selection]), role: .destructive) {
                        Task { await model.delete() }
                    }
                }
                Button(tr("form.cancel"), action: onDone)
            }
            .padding()
        }
    }

    private var oddsFieldTitle: String {
        switch model.oddsFormat {
        case "american": return tr("form.americanOdds")
        case "fractional": return "\(tr("bets.odds")) (11/8)"
        case "hong_kong": return tr("form.hongKongOdds")
        case "malaysian": return tr("form.malaysianOdds")
        case "indonesian": return tr("form.indonesianOdds")
        default: return tr("form.decimalOdds")
        }
    }

    private var oddsKeyboard: UIKeyboardType {
        switch model.oddsFormat {
        case "american", "malaysian", "indonesian", "fractional":
            return .default
        default:
            return .decimalPad
        }
    }

    private func oddsFormatLabel(_ format: String) -> String {
        switch format {
        case "american": return tr("form.american")
        case "fractional": return tr("form.fractional")
        case "hong_kong": return tr("form.hong_kong")
        case "malaysian": return tr("form.malaysian")
        case "indonesian": return tr("form.indonesian")
        default: return tr("form.decimal")
        }
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.headline)
            .padding(.top, 4)
    }

    @ViewBuilder
    private func edgeRow(label: String, edge: Double?, kelly: BetMath.KellyResult?) -> some View {
        if let edge {
            VStack(alignment: .leading, spacing: 2) {
                Text("\(label): \(String(format: "%.2f", edge))%")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if let kelly, model.bankroll > 0 {
                    if kelly.fraction > 0 {
                        Text(tr("form.kellySuggest", params: [
                            "stake": String(format: "%.2f", kelly.stake),
                            "currency": model.currency,
                            "pct": String(format: "%.1f", kelly.fraction * 100),
                        ]))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    } else {
                        Text(tr("form.kellyNoEdge")).font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }
        }
    }
}

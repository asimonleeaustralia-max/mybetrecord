import SwiftUI

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
                model = BetEditorModel(betId: betId, betsRepository: environment.betsRepository)
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

    private let outcomes = ["pending", "win", "loss", "void", "half_win", "half_loss", "placed"]

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
            VStack(alignment: .leading, spacing: 10) {
                if let error = model.errorMessage { ErrorText(message: error) }
                AppTextField(title: tr("form.sport"), text: $model.sport)
                AppTextField(title: tr("form.betType"), text: $model.betType)
                if !model.isEdit { Toggle(tr("form.multiple"), isOn: $model.isMultiple) }
                Picker("", selection: $model.oddsFormat) {
                    Text(tr("form.decimal")).tag("decimal")
                    Text(tr("form.fractional")).tag("fractional")
                }
                .pickerStyle(.segmented)

                if model.isMultiple {
                    ForEach(Array(model.legs.indices), id: \.self) { index in
                        VStack(alignment: .leading) {
                            Text(tr("form.legLabel", params: ["n": "\(index + 1)"]))
                            AppTextField(title: tr("form.event"), text: $model.legs[index].event)
                            AppTextField(title: tr("form.selection"), text: $model.legs[index].selection)
                            AppTextField(title: tr("bets.odds"), text: $model.legs[index].odds, keyboard: model.oddsFormat == "fractional" ? .default : .decimalPad)
                        }
                        .padding()
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 8))
                    }
                    Button(tr("form.addSelection")) {
                        if model.legs.count < 10 { model.legs.append(LegInput()) }
                    }
                    if let combined = model.currentDecimalOdds() {
                        Text("\(tr("form.combinedOdds")): \(String(format: "%.2f", combined))")
                    }
                } else {
                    AppTextField(title: tr("form.event"), text: $model.event)
                    AppTextField(title: tr("form.selection"), text: $model.selection)
                    AppTextField(title: tr("form.decimalOdds"), text: $model.odds, keyboard: model.oddsFormat == "fractional" ? .default : .decimalPad)
                    Toggle(tr("form.eachWay"), isOn: $model.eachWay)
                    Toggle(tr("form.freeBet"), isOn: $model.freeBet)
                }

                AppTextField(title: tr("form.eventAt"), text: $model.eventAt)
                AppTextField(title: tr("form.stake"), text: $model.stake, keyboard: .decimalPad)
                AppTextField(title: tr("form.currency"), text: $model.currency)
                ChoicePicker(label: tr("form.result"), options: outcomes.map { ($0, tr("outcomes.\($0)")) }, selection: $model.outcome)
                AppTextField(title: tr("form.cashOut"), text: $model.cashOut, keyboard: .decimalPad)
                AppTextField(title: tr("form.closingOdds"), text: $model.closingOdds, keyboard: .decimalPad)
                AppTextField(title: tr("form.bookmaker"), text: $model.bookmaker)
                AppTextField(title: tr("form.tipster"), text: $model.tipster)
                AppTextField(title: tr("form.notes"), text: $model.notes, axis: .vertical)

                Button(model.isEdit ? tr("form.saveChanges") : tr("form.saveBet")) {
                    Task { await model.save() }
                }
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
                .disabled(model.saving)

                if model.isEdit {
                    if model.shareToken == nil {
                        Button(tr("share.shareBet")) { Task { await model.createShareLink() } }
                    } else {
                        Button(tr("share.copyLink")) { showShare = true }
                        Button(tr("share.revokeLink"), role: .destructive) { Task { await model.revokeShareLink() } }
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
}

import SwiftUI
import UIKit

struct SettingsView: View {
    @EnvironmentObject private var auth: AuthRepository
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var i18n: I18n
    @State private var user: User?
    @State private var loading = true
    @State private var saving = false
    @State private var error: String?
    @State private var info: String?
    @State private var locale = "en"
    @State private var displayName = ""
    @State private var baseCurrency = "GBP"
    @State private var bankroll = ""
    @State private var kellyMultiplier = ""
    @State private var timezone = ""
    @State private var defaultOddsFormat = "decimal"
    @State private var publicBetsEnabled = false
    @State private var accountDescription = ""
    @State private var showDeleteDialog = false
    @State private var deletePassword = ""
    @State private var deleteConfirm = ""
    @State private var shareProfile = false

    private let oddsFormats = [
        ("decimal", "settings.oddsDecimal"),
        ("american", "settings.oddsAmerican"),
        ("fractional", "settings.oddsFractional"),
        ("hong_kong", "settings.oddsHongKong"),
        ("malaysian", "settings.oddsMalaysian"),
        ("indonesian", "settings.oddsIndonesian"),
    ]

    var body: some View {
        Group {
            if loading && user == nil {
                LoadingView()
            } else {
                form
            }
        }
        .navigationTitle(tr("settings.title"))
        .task { await load() }
        .sheet(isPresented: $showDeleteDialog) {
            DeleteAccountSheet(
                deletePassword: $deletePassword,
                deleteConfirm: $deleteConfirm,
                onCancel: { showDeleteDialog = false },
                onDelete: { Task { await deleteAccount() } }
            )
        }
        .sheet(isPresented: $shareProfile) {
            if let token = user?.publicBetsToken {
                ShareSheet(items: [Formatters.publicProfileURL(token: token)])
            }
        }
    }

    private var form: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("settings.title")).font(.title2)
                Text(tr("settings.subtitle"))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                if let error { ErrorText(message: error) }
                if let info { Text(info).foregroundStyle(.secondary) }
                if let user {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(tr("plan.title")).font(.headline)
                        Text("\(tr("settings.email")): \(user.email)")
                        Text("\(tr("plan.title")): \(user.plan.uppercased())\(user.isPro ? " (Pro)" : "")")
                        Text(tr("settings.planNote")).font(.footnote).foregroundStyle(.secondary)
                    }
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                Text(tr("settings.preferences")).font(.headline)
                Picker(tr("settings.language"), selection: $locale) {
                    ForEach(i18n.languages, id: \.code) { lang in
                        Text(lang.label).tag(lang.code)
                    }
                }
                .onChange(of: locale) { newValue in
                    i18n.switchLocale(newValue)
                    AppPreferences.locale = newValue
                }
                AppTextField(title: tr("settings.publicNickname"), text: $displayName)
                AppTextField(title: tr("settings.defaultCurrency"), text: $baseCurrency)
                AppTextField(title: tr("settings.bankroll"), text: $bankroll, keyboard: .decimalPad)
                AppTextField(title: tr("settings.kellyMultiplier"), text: $kellyMultiplier, keyboard: .decimalPad)
                AppTextField(title: tr("settings.timezone"), text: $timezone)
                ChoicePicker(
                    label: tr("settings.defaultOdds"),
                    options: oddsFormats.map { ($0.0, tr($0.1)) },
                    selection: $defaultOddsFormat
                )
                Toggle(tr("settings.publicBetsEnabled"), isOn: $publicBetsEnabled)
                if publicBetsEnabled {
                    AppTextField(title: tr("settings.accountDescription"), text: $accountDescription, axis: .vertical)
                    if user?.publicBetsToken != nil {
                        Button(tr("settings.shareProfile")) { shareProfile = true }
                    }
                }
                Button(tr("settings.save"), action: save)
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                    .disabled(saving)
                Text(tr("settings.legal")).font(.headline)
                LinkButton(title: tr("settings.privacy")) { open("https://www.mybetrecord.com/privacy") }
                LinkButton(title: tr("settings.terms")) { open("https://www.mybetrecord.com/terms") }
                LinkButton(title: tr("settings.responsibleGambling")) { open("https://www.mybetrecord.com/responsible-gambling") }
                LinkButton(title: tr("settings.deleteAccountWeb")) { open("https://www.mybetrecord.com/delete-account") }
                Button(tr("nav.signOut"), role: .destructive) {
                    Task {
                        await auth.logout()
                        environment.betsRepository.clearLocalData()
                    }
                }
                    .frame(maxWidth: .infinity)
                Button(tr("settings.deleteAccount")) { showDeleteDialog = true }
                    .frame(maxWidth: .infinity)
            }
            .padding()
        }
        .id(i18n.locale)
    }

    private func load() async {
        loading = true
        defer { loading = false }
        do {
            let loaded = try await auth.me()
            user = loaded
            locale = loaded.preferredLocale
            displayName = loaded.displayName ?? ""
            baseCurrency = loaded.baseCurrency
            bankroll = String(loaded.bankroll)
            kellyMultiplier = String(loaded.kellyMultiplier)
            timezone = loaded.timezone
            defaultOddsFormat = loaded.defaultOddsFormat
            publicBetsEnabled = loaded.publicBetsEnabled
            accountDescription = loaded.accountDescription ?? ""
            error = nil
        } catch {
            if error.isConnectivityError {
                self.error = nil
                self.info = tr("bets.offlineCached")
            } else {
                self.error = error.userMessage
            }
        }
    }

    private func save() {
        saving = true
        error = nil
        info = nil
        Task {
            defer { saving = false }
            do {
                let update = SettingsUpdate(
                    defaultOddsFormat: defaultOddsFormat,
                    baseCurrency: baseCurrency.uppercased(),
                    bankroll: Double(bankroll),
                    kellyMultiplier: Double(kellyMultiplier),
                    preferredLocale: locale,
                    timezone: timezone,
                    publicBetsEnabled: publicBetsEnabled,
                    accountDescription: accountDescription.nilIfBlank,
                    displayName: displayName.nilIfBlank
                )
                user = try await auth.updateSettings(update)
                i18n.switchLocale(locale)
                info = tr("settings.saved")
            } catch {
                self.error = error.userMessage
            }
        }
    }

    private func deleteAccount() async {
        guard deleteConfirm == "DELETE" else {
            error = tr("settings.typeDelete")
            return
        }
        do {
            try await auth.deleteAccount(password: deletePassword)
            environment.betsRepository.clearLocalData()
        } catch {
            self.error = error.userMessage
        }
    }

    private func open(_ url: String) {
        guard let link = URL(string: url) else { return }
        UIApplication.shared.open(link)
    }
}

private struct LinkButton: View {
    let title: String
    let action: () -> Void
    var body: some View {
        Button(title, action: action).frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct DeleteAccountSheet: View {
    @Binding var deletePassword: String
    @Binding var deleteConfirm: String
    let onCancel: () -> Void
    let onDelete: () -> Void

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("settings.deleteAccountBody"))
                SecureField(tr("auth.password"), text: $deletePassword)
                TextField(tr("settings.typeDelete"), text: $deleteConfirm)
                Button(tr("settings.deleteForever"), role: .destructive, action: onDelete)
                    .frame(maxWidth: .infinity)
            }
            .padding()
            .navigationTitle(tr("settings.deleteAccount"))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(tr("common.cancel"), action: onCancel)
                }
            }
        }
    }
}

private extension String {
    var nilIfBlank: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}

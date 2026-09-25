import Foundation

@MainActor
final class AuthRepository: ObservableObject {
    private let api: APIClient
    private let tokenStore: TokenStore

    @Published private(set) var isLoggedIn: Bool

    init(api: APIClient, tokenStore: TokenStore) {
        self.api = api
        self.tokenStore = tokenStore
        self.isLoggedIn = tokenStore.hasSession()
    }

    func login(email: String, password: String) async throws {
        let tokens = try await api.login(email: email, password: password)
        persistTokens(tokens)
        isLoggedIn = true
    }

    func register(email: String, password: String, timezone: String?) async throws -> String {
        let response = try await api.register(email: email, password: password, timezone: timezone)
        return response.message
    }

    func requestPasswordReset(email: String) async throws {
        try await api.requestPasswordReset(email: email)
    }

    func confirmPasswordReset(token: String, newPassword: String) async throws {
        try await api.confirmPasswordReset(token: token, password: newPassword)
    }

    func refreshAccessToken() async -> TokenResponse? {
        guard let refresh = tokenStore.getRefreshToken() else { return nil }
        do {
            let tokens = try await api.refresh(refreshToken: refresh)
            persistTokens(tokens)
            return tokens
        } catch {
            // Dead spots / offline must not sign the user out.
            if error.isConnectivityError { return nil }
            if let api = error as? APIError, case .offline = api { return nil }
            if let api = error as? APIError, case .http(let status, _) = api, status >= 500 {
                return nil
            }
            tokenStore.clear()
            isLoggedIn = false
            return nil
        }
    }

    func logout() async {
        let refresh = tokenStore.getRefreshToken()
        do {
            if let refresh, !refresh.isEmpty {
                try await api.logout(refreshToken: refresh)
            }
        } catch {}
        tokenStore.clear()
        isLoggedIn = false
    }

    func me() async throws -> User {
        let user = try await api.me()
        syncLocale(user)
        return user
    }

    func updateSettings(_ update: SettingsUpdate) async throws -> User {
        let user = try await api.updateSettings(update)
        syncLocale(user)
        return user
    }

    func deleteAccount(password: String) async throws {
        try await api.deleteAccount(password: password)
        tokenStore.clear()
        isLoggedIn = false
    }

    func persistTokens(_ tokens: TokenResponse) {
        tokenStore.setAccessToken(tokens.accessToken)
        if let refresh = tokens.refreshToken {
            tokenStore.setRefreshToken(refresh)
        }
        isLoggedIn = true
    }

    func clearSession() {
        tokenStore.clear()
        isLoggedIn = false
    }

    private func syncLocale(_ user: User) {
        if let normalized = I18n.normalize(user.preferredLocale) {
            I18n.shared.switchLocale(normalized)
            AppPreferences.locale = normalized
        }
    }
}

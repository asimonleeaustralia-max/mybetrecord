import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case http(status: Int, body: String)
    case decoding(Error)
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .http(let status, let body):
            if body.contains("detail") { return String(body.prefix(200)) }
            switch status {
            case 401: return "Session expired. Please sign in again."
            case 403: return "You do not have permission for this action."
            case 422: return "Please check the form and try again."
            default: return "Request failed (\(status))"
            }
        case .decoding:
            return "Unexpected response from server"
        case .unauthorized:
            return "Session expired. Please sign in again."
        }
    }
}

enum AppConfig {
    static var baseURL: URL {
        if let urlString = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           let url = URL(string: urlString) {
            return url
        }
        return URL(string: "https://www.mybetrecord.com")!
    }
}

actor TokenRefreshCoordinator {
    private let tokenStore: TokenStore
    private let baseURL: URL
    private var refreshTask: Task<TokenResponse?, Never>?

    init(tokenStore: TokenStore, baseURL: URL) {
        self.tokenStore = tokenStore
        self.baseURL = baseURL
    }

    func refreshIfNeeded(requestToken: String?) async -> String? {
        let current = tokenStore.getAccessToken()
        if let current, !current.isEmpty, current != requestToken {
            return current
        }
        if let refreshTask {
            let result = await refreshTask.value
            return result?.accessToken
        }
        let task = Task<TokenResponse?, Never> {
            guard let refresh = tokenStore.getRefreshToken() else { return nil }
            return await Self.performRefresh(baseURL: baseURL, refreshToken: refresh)
        }
        refreshTask = task
        let result = await task.value
        refreshTask = nil
        if let result {
            tokenStore.setAccessToken(result.accessToken)
            if let rt = result.refreshToken {
                tokenStore.setRefreshToken(rt)
            }
            return result.accessToken
        }
        tokenStore.clear()
        return nil
    }

    private static func performRefresh(baseURL: URL, refreshToken: String) async -> TokenResponse? {
        let url = baseURL.appendingPathComponent("auth/refresh")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let body = RefreshRequest(refreshToken: refreshToken)
        guard let data = try? JSONEncoder.api.encode(body) else { return nil }
        request.httpBody = data
        do {
            let (responseData, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                return nil
            }
            return try JSONDecoder.api.decode(TokenResponse.self, from: responseData)
        } catch {
            return nil
        }
    }
}

final class APIClient: @unchecked Sendable {
    let tokenStore: TokenStore
    private let baseURL: URL
    private let refreshCoordinator: TokenRefreshCoordinator
    private let encoder = JSONEncoder.api
    private let decoder = JSONDecoder.api

    init(tokenStore: TokenStore, baseURL: URL = AppConfig.baseURL) {
        self.tokenStore = tokenStore
        self.baseURL = baseURL
        self.refreshCoordinator = TokenRefreshCoordinator(tokenStore: tokenStore, baseURL: baseURL)
    }

    func request<T: Decodable>(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil,
        query: [URLQueryItem] = [],
        skipAuth: Bool = false,
        retryOn401: Bool = true
    ) async throws -> T {
        let data = try await requestData(method, path: path, body: body, query: query, skipAuth: skipAuth, retryOn401: retryOn401)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func requestVoid(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil,
        skipAuth: Bool = false,
        retryOn401: Bool = true
    ) async throws {
        _ = try await requestData(method, path: path, body: body, skipAuth: skipAuth, retryOn401: retryOn401)
    }

    func requestData(
        _ method: String,
        path: String,
        body: (any Encodable)? = nil,
        query: [URLQueryItem] = [],
        skipAuth: Bool = false,
        retryOn401: Bool = true
    ) async throws -> Data {
        let requestToken = skipAuth ? nil : tokenStore.getAccessToken()
        var request = try buildRequest(method, path: path, body: body, query: query, accessToken: requestToken, skipAuth: skipAuth)
        var (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode == 401, !skipAuth, retryOn401 {
            if let newToken = await refreshCoordinator.refreshIfNeeded(requestToken: requestToken) {
                request = try buildRequest(method, path: path, body: body, query: query, accessToken: newToken, skipAuth: false)
                (data, response) = try await URLSession.shared.data(for: request)
            } else {
                throw APIError.unauthorized
            }
        }
        guard let http = response as? HTTPURLResponse else {
            throw APIError.http(status: -1, body: "")
        }
        guard (200..<300).contains(http.statusCode) else {
            let bodyText = String(data: data, encoding: .utf8) ?? ""
            throw APIError.http(status: http.statusCode, body: bodyText)
        }
        return data
    }

    private func buildRequest(
        _ method: String,
        path: String,
        body: (any Encodable)?,
        query: [URLQueryItem],
        accessToken: String?,
        skipAuth: Bool
    ) throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)
        if !query.isEmpty { components?.queryItems = query }
        guard let url = components?.url else { throw APIError.invalidURL }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try encoder.encode(AnyEncodable(body))
        }
        if !skipAuth, let accessToken {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }
        return request
    }
}

private struct AnyEncodable: Encodable {
    let value: any Encodable
    init(_ value: any Encodable) { self.value = value }
    func encode(to encoder: Encoder) throws { try value.encode(to: encoder) }
}

extension JSONEncoder {
    static let api: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()
}

extension JSONDecoder {
    static let api: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
}

extension APIClient {
    // MARK: Auth

    func login(email: String, password: String) async throws -> TokenResponse {
        let body = LoginRequest(
            email: email.trimmingCharacters(in: .whitespacesAndNewlines),
            password: password,
            client: "ios",
            deviceName: UIDeviceName.current
        )
        return try await request("POST", path: "auth/login", body: body, skipAuth: true, retryOn401: false)
    }

    func register(email: String, password: String, timezone: String?) async throws -> RegisterResponse {
        let body = RegisterRequest(
            email: email.trimmingCharacters(in: .whitespacesAndNewlines),
            password: password,
            timezone: timezone
        )
        return try await request("POST", path: "auth/register", body: body, skipAuth: true, retryOn401: false)
    }

    func refresh(refreshToken: String) async throws -> TokenResponse {
        try await request("POST", path: "auth/refresh", body: RefreshRequest(refreshToken: refreshToken), skipAuth: true, retryOn401: false)
    }

    func requestPasswordReset(email: String) async throws {
        try await requestVoid("POST", path: "auth/password-reset/request", body: PasswordResetRequest(email: email.trimmingCharacters(in: .whitespacesAndNewlines)), skipAuth: true, retryOn401: false)
    }

    func confirmPasswordReset(token: String, password: String) async throws {
        do {
            try await requestVoid("POST", path: "auth/password-reset/confirm", body: PasswordResetConfirm(token: token.trimmingCharacters(in: .whitespacesAndNewlines), password: password), skipAuth: true, retryOn401: false)
        } catch let APIError.http(status, _) where status == 400 || status == 422 {
            throw NSError(domain: "Auth", code: status, userInfo: [NSLocalizedDescriptionKey: "That code is invalid or has expired. Request a new one."])
        }
    }

    func logout(refreshToken: String?) async throws {
        try await requestVoid("POST", path: "auth/logout", body: LogoutRequest(refreshToken: refreshToken, allDevices: false), skipAuth: false, retryOn401: false)
    }

    func me() async throws -> User {
        try await request("GET", path: "auth/me")
    }

    func updateSettings(_ update: SettingsUpdate) async throws -> User {
        try await request("PATCH", path: "auth/settings", body: update)
    }

    func deleteAccount(password: String) async throws {
        try await requestVoid("DELETE", path: "auth/account", body: AccountDeleteRequest(password: password, confirm: "DELETE"))
    }

    // MARK: Bets

    func listBets(limit: Int = 200, offset: Int = 0) async throws -> [Bet] {
        try await request("GET", path: "bets", query: [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)"),
        ])
    }

    func getBet(id: String) async throws -> Bet {
        try await request("GET", path: "bets/\(id)")
    }

    func createBet(_ body: BetCreate) async throws -> Bet {
        try await request("POST", path: "bets", body: body)
    }

    func updateBet(id: String, body: BetUpdate) async throws -> Bet {
        try await request("PATCH", path: "bets/\(id)", body: body)
    }

    func deleteBet(id: String) async throws {
        try await requestVoid("DELETE", path: "bets/\(id)")
    }

    func createShareLink(id: String) async throws -> BetShare {
        try await request("POST", path: "bets/\(id)/share")
    }

    func revokeShareLink(id: String) async throws {
        try await requestVoid("DELETE", path: "bets/\(id)/share")
    }

    func listSports() async throws -> [String] {
        try await request("GET", path: "bets/sports")
    }

    func listBetTypes() async throws -> [String] {
        try await request("GET", path: "bets/bet-types")
    }

    // MARK: Reports

    func reportSummary(usePrimaryCurrency: Bool = true) async throws -> ReportSummary {
        try await request("GET", path: "reports/summary", query: [
            URLQueryItem(name: "use_primary_currency", value: usePrimaryCurrency ? "true" : "false"),
        ])
    }

    func equityCurve() async throws -> [EquityPoint] {
        try await request("GET", path: "reports/equity-curve")
    }

    func exportReport(kind: String) async throws -> Data {
        try await requestData("GET", path: "reports/export.\(kind)")
    }
}

#if canImport(UIKit)
import UIKit
enum UIDeviceName {
    static var current: String { UIDevice.current.name }
}
#else
enum UIDeviceName {
    static var current: String { "iOS Simulator" }
}
#endif

extension Error {
    var userMessage: String {
        if let api = self as? APIError, let desc = api.errorDescription { return desc }
        if let localized = (self as NSError).userInfo[NSLocalizedDescriptionKey] as? String { return localized }
        if let url = self as? URLError { return "Network error. Check your connection." }
        return localizedDescription.isEmpty ? "Something went wrong" : localizedDescription
    }
}

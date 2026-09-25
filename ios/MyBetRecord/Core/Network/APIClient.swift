import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case http(status: Int, body: String)
    case decoding(Error)
    case unauthorized
    case offline(message: String)

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
        case .offline(let message):
            return message
        }
    }
}

enum TokenRefreshResult {
    case refreshed(String)
    /// Access token was already updated by another concurrent refresh.
    case current(String)
    /// Refresh token rejected — session is gone.
    case unauthorized
    /// Network/dead-spot failure — keep the existing session and retry later.
    case transientFailure
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
    private var refreshTask: Task<TokenRefreshResult, Never>?

    init(tokenStore: TokenStore, baseURL: URL) {
        self.tokenStore = tokenStore
        self.baseURL = baseURL
    }

    func refreshIfNeeded(requestToken: String?) async -> TokenRefreshResult {
        let current = tokenStore.getAccessToken()
        if let current, !current.isEmpty, current != requestToken {
            return .current(current)
        }
        if let refreshTask {
            return await refreshTask.value
        }
        let task = Task<TokenRefreshResult, Never> {
            guard let refresh = tokenStore.getRefreshToken(), !refresh.isEmpty else {
                return .unauthorized
            }
            switch await Self.performRefresh(baseURL: baseURL, refreshToken: refresh) {
            case .success(let tokens):
                tokenStore.setAccessToken(tokens.accessToken)
                if let rt = tokens.refreshToken {
                    tokenStore.setRefreshToken(rt)
                }
                return .refreshed(tokens.accessToken)
            case .unauthorized:
                tokenStore.clear()
                return .unauthorized
            case .transientFailure:
                return .transientFailure
            }
        }
        refreshTask = task
        let result = await task.value
        refreshTask = nil
        return result
    }

    private enum RefreshAttempt {
        case success(TokenResponse)
        case unauthorized
        case transientFailure
    }

    private static func performRefresh(baseURL: URL, refreshToken: String) async -> RefreshAttempt {
        let url = baseURL.appendingPathComponent("auth/refresh")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 15
        let body = RefreshRequest(refreshToken: refreshToken)
        guard let data = try? JSONEncoder.api.encode(body) else { return .unauthorized }
        request.httpBody = data
        do {
            let (responseData, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                return .transientFailure
            }
            if (200..<300).contains(http.statusCode) {
                do {
                    let tokens = try JSONDecoder.api.decode(TokenResponse.self, from: responseData)
                    return .success(tokens)
                } catch {
                    return .unauthorized
                }
            }
            if http.statusCode == 401 || http.statusCode == 403 {
                return .unauthorized
            }
            // 5xx / unexpected — treat as transient so dead spots or outages don't force logout.
            return .transientFailure
        } catch {
            return error.isConnectivityError ? .transientFailure : .transientFailure
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
        try await performRequestData(method, path: path, body: body, query: query, skipAuth: skipAuth, retryOn401: retryOn401)
    }

    private func performRequestData(
        _ method: String,
        path: String,
        body: (any Encodable)?,
        query: [URLQueryItem],
        skipAuth: Bool,
        retryOn401: Bool
    ) async throws -> Data {
        let requestToken = skipAuth ? nil : tokenStore.getAccessToken()
        var request = try buildRequest(method, path: path, body: body, query: query, accessToken: requestToken, skipAuth: skipAuth)
        var (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, http.statusCode == 401, !skipAuth, retryOn401 {
            switch await refreshCoordinator.refreshIfNeeded(requestToken: requestToken) {
            case .refreshed(let newToken), .current(let newToken):
                request = try buildRequest(method, path: path, body: body, query: query, accessToken: newToken, skipAuth: false)
                (data, response) = try await URLSession.shared.data(for: request)
            case .unauthorized:
                throw APIError.unauthorized
            case .transientFailure:
                throw APIError.offline(message: "Connection interrupted. Try again when you have a signal.")
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
        request.timeoutInterval = 20
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
    var isConnectivityError: Bool {
        if let api = self as? APIError, case .offline = api { return true }
        if let urlError = self as? URLError {
            switch urlError.code {
            case .notConnectedToInternet,
                 .networkConnectionLost,
                 .timedOut,
                 .cannotConnectToHost,
                 .cannotFindHost,
                 .dnsLookupFailed,
                 .internationalRoamingOff,
                 .dataNotAllowed,
                 .secureConnectionFailed,
                 .cannotLoadFromNetwork:
                return true
            default:
                return false
            }
        }
        let ns = self as NSError
        guard ns.domain == NSURLErrorDomain else { return false }
        switch ns.code {
        case NSURLErrorNotConnectedToInternet,
             NSURLErrorNetworkConnectionLost,
             NSURLErrorTimedOut,
             NSURLErrorCannotConnectToHost,
             NSURLErrorCannotFindHost,
             NSURLErrorDNSLookupFailed,
             NSURLErrorInternationalRoamingOff,
             NSURLErrorDataNotAllowed,
             NSURLErrorSecureConnectionFailed,
             NSURLErrorCannotLoadFromNetwork:
            return true
        default:
            return false
        }
    }

    var userMessage: String {
        if let api = self as? APIError, let desc = api.errorDescription { return desc }
        if isConnectivityError {
            return "No internet connection. Check your signal and try again."
        }
        if let localized = (self as NSError).userInfo[NSLocalizedDescriptionKey] as? String {
            // Replace the system "The Internet connection appears to be offline" phrasing.
            let lower = localized.lowercased()
            if lower.contains("appears to be offline")
                || lower.contains("internet connection")
                || lower.contains("network connection was lost") {
                return "No internet connection. Check your signal and try again."
            }
            return localized
        }
        return localizedDescription.isEmpty ? "Something went wrong" : localizedDescription
    }
}

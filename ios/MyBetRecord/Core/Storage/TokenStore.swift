import Foundation
import Security

enum KeychainTokenStore {
    private static let service = "com.mybetrecord.ios.tokens"
    private static let refreshAccount = "refresh_token"

    static func getRefreshToken() -> String? {
        read(account: refreshAccount)
    }

    static func setRefreshToken(_ token: String) {
        save(account: refreshAccount, value: token)
    }

    static func clear() {
        delete(account: refreshAccount)
    }

    private static func save(account: String, value: String) {
        delete(account: account)
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    private static func read(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private static func delete(account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

final class TokenStore: @unchecked Sendable {
    private let lock = NSLock()
    private var accessToken: String?

    func getAccessToken() -> String? {
        lock.lock()
        defer { lock.unlock() }
        return accessToken
    }

    func setAccessToken(_ token: String) {
        lock.lock()
        accessToken = token
        lock.unlock()
    }

    func getRefreshToken() -> String? {
        KeychainTokenStore.getRefreshToken()
    }

    func setRefreshToken(_ token: String) {
        KeychainTokenStore.setRefreshToken(token)
    }

    func hasSession() -> Bool {
        getAccessToken() != nil || getRefreshToken() != nil
    }

    func clear() {
        lock.lock()
        accessToken = nil
        lock.unlock()
        KeychainTokenStore.clear()
    }
}

enum AppPreferences {
    private static let ageKey = "mbr_age_attested"
    private static let localeKey = "mbr_locale"

    static var ageAttested: Bool {
        get { UserDefaults.standard.bool(forKey: ageKey) }
        set { UserDefaults.standard.set(newValue, forKey: ageKey) }
    }

    static var locale: String? {
        get { UserDefaults.standard.string(forKey: localeKey) }
        set {
            if let newValue {
                UserDefaults.standard.set(newValue, forKey: localeKey)
            } else {
                UserDefaults.standard.removeObject(forKey: localeKey)
            }
        }
    }
}

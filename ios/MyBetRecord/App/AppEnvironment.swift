import Foundation

@MainActor
final class AppEnvironment: ObservableObject {
    let tokenStore = TokenStore()
    lazy var apiClient = APIClient(tokenStore: tokenStore)
    lazy var authRepository = AuthRepository(api: apiClient, tokenStore: tokenStore)
    lazy var reportsRepository = ReportsRepository(api: apiClient)

    let betCacheStorage: BetCacheStorage

    lazy var betsRepository = BetsRepository(api: apiClient, cacheStorage: betCacheStorage)

    init() {
        betCacheStorage = BetCacheStorage()
        if let locale = AppPreferences.locale {
            I18n.shared.switchLocale(locale)
        }
    }
}

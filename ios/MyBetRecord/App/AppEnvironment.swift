import Foundation

@MainActor
final class AppEnvironment: ObservableObject {
    let tokenStore = TokenStore()
    lazy var apiClient = APIClient(tokenStore: tokenStore)
    lazy var authRepository = AuthRepository(api: apiClient, tokenStore: tokenStore)
    lazy var reportsRepository = ReportsRepository(api: apiClient)

    let betCacheStorage: BetCacheStorage
    let syncOutbox: SyncOutbox
    let networkMonitor = NetworkMonitor()

    lazy var betsRepository = BetsRepository(
        api: apiClient,
        cacheStorage: betCacheStorage,
        outbox: syncOutbox
    )

    init() {
        betCacheStorage = BetCacheStorage()
        syncOutbox = SyncOutbox()
        if let locale = AppPreferences.locale {
            I18n.shared.switchLocale(locale)
        }
    }

    func startNetworkMonitoring() {
        networkMonitor.start { [weak self] in
            self?.betsRepository.scheduleSync()
        }
        betsRepository.scheduleSync()
    }
}

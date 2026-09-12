import Foundation
import SwiftData

@MainActor
final class AppEnvironment: ObservableObject {
    let tokenStore = TokenStore()
    lazy var apiClient = APIClient(tokenStore: tokenStore)
    lazy var authRepository = AuthRepository(api: apiClient, tokenStore: tokenStore)
    lazy var reportsRepository = ReportsRepository(api: apiClient)

    let modelContainer: ModelContainer
    private var modelContext: ModelContext { modelContainer.mainContext }

    lazy var betsRepository = BetsRepository(api: apiClient, modelContext: modelContext)

    init() {
        do {
            modelContainer = try ModelContainer(for: BetCacheEntity.self)
        } catch {
            fatalError("Failed to create model container: \(error)")
        }
        if let locale = AppPreferences.locale {
            I18n.shared.switchLocale(locale)
        }
    }
}

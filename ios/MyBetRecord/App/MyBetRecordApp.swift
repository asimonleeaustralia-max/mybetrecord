import SwiftUI
import SwiftData

@main
struct MyBetRecordApp: App {
    @StateObject private var environment = AppEnvironment()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(environment)
                .environmentObject(environment.authRepository)
                .environmentObject(I18n.shared)
                .modelContainer(environment.modelContainer)
        }
    }
}

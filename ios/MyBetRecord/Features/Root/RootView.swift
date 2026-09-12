import SwiftUI

struct RootView: View {
    @EnvironmentObject private var auth: AuthRepository
    @State private var ageAttested = AppPreferences.ageAttested
    @State private var showForgotPassword = false

    var body: some View {
        Group {
            if !ageAttested {
                AgeGateView {
                    AppPreferences.ageAttested = true
                    ageAttested = true
                }
            } else if auth.isLoggedIn {
                MainTabView()
            } else if showForgotPassword {
                ForgotPasswordView(onBack: { showForgotPassword = false })
            } else {
                AuthView(onForgotPassword: { showForgotPassword = true })
            }
        }
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            NavigationStack {
                DashboardView()
            }
            .tabItem { Label(tr("android.home"), systemImage: "house") }

            NavigationStack {
                BetsTab()
            }
            .tabItem { Label(tr("nav.bets"), systemImage: "list.bullet") }

            NavigationStack {
                ReportsView()
            }
            .tabItem { Label(tr("nav.reports"), systemImage: "chart.bar") }

            NavigationStack {
                ToolsView()
            }
            .tabItem { Label(tr("android.tools"), systemImage: "function") }

            NavigationStack {
                SettingsView()
            }
            .tabItem { Label(tr("nav.settings"), systemImage: "gearshape") }
        }
    }
}

private struct BetsTab: View {
    @State private var editorRoute: BetEditorRoute?

    var body: some View {
        BetsListView(onOpenBet: { editorRoute = BetEditorRoute(id: $0) })
            .navigationDestination(item: $editorRoute) { route in
                BetEditorView(betId: route.id, onDone: { editorRoute = nil })
            }
    }
}

struct BetEditorRoute: Identifiable, Hashable {
    let id: String
}

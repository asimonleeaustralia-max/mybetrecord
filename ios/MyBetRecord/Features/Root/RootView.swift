import SwiftUI

struct RootView: View {
    @EnvironmentObject private var auth: AuthRepository
    @EnvironmentObject private var i18n: I18n
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
        // Re-evaluate labels when the active locale changes.
        .id(i18n.locale)
    }
}

struct MainTabView: View {
    @EnvironmentObject private var i18n: I18n

    var body: some View {
        TabView {
            NavigationView {
                DashboardView()
            }
            .tabItem { Label(tr("nav.home"), systemImage: "house") }

            NavigationView {
                BetsTab()
            }
            .tabItem { Label(tr("nav.bets"), systemImage: "list.bullet") }

            NavigationView {
                ReportsView()
            }
            .tabItem { Label(tr("nav.reports"), systemImage: "chart.bar") }

            NavigationView {
                ToolsView()
            }
            .tabItem { Label(tr("nav.tools"), systemImage: "function") }

            NavigationView {
                SettingsView()
            }
            .tabItem { Label(tr("nav.settings"), systemImage: "gearshape") }
        }
        .id(i18n.locale)
    }
}

private struct BetsTab: View {
    @State private var editorRoute: BetEditorRoute?
    
    private var isShowingEditor: Binding<Bool> {
        Binding(
            get: { editorRoute != nil },
            set: { if !$0 { editorRoute = nil } }
        )
    }

    var body: some View {
        ZStack {
            BetsListView(onOpenBet: { editorRoute = BetEditorRoute(id: $0) })
            
            NavigationLink(
                destination: editorRoute.map { route in
                    AnyView(BetEditorView(betId: route.id, onDone: { editorRoute = nil }))
                } ?? AnyView(EmptyView()),
                isActive: isShowingEditor
            ) {
                EmptyView()
            }
            .hidden()
        }
    }
}

struct BetEditorRoute: Identifiable, Hashable {
    let id: String
}

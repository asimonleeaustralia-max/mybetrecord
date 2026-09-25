import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var summary: ReportSummary?
    @State private var loading = false
    @State private var statusMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("dashboard.title")).font(.title2)
                Text(tr("dashboard.subtitle")).foregroundStyle(.secondary)
                if let statusMessage {
                    Text(statusMessage)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                if let summary {
                    let currency = summary.currency ?? summary.baseCurrency
                    MetricCard(label: tr("dashboard.pl"), value: Formatters.money(summary.profit, currency: currency))
                    MetricCard(label: tr("dashboard.turnover"), value: Formatters.money(summary.turnover, currency: currency))
                    MetricCard(label: tr("dashboard.yield"), value: String(format: "%.2f%%", summary.yieldPct))
                    MetricCard(label: tr("dashboard.strikeRate"), value: String(format: "%.2f%%", summary.strikeRatePct))
                    MetricCard(label: tr("dashboard.totalBets"), value: "\(summary.settledBets) / \(summary.totalBets)")
                    if let bankroll = summary.bankroll {
                        MetricCard(label: tr("dashboard.bankroll"), value: Formatters.money(bankroll, currency: summary.baseCurrency))
                    }
                } else if loading {
                    LoadingView()
                }
            }
            .padding()
        }
        .refreshable { await refresh() }
        .task { await refresh() }
        .onChange(of: environment.betsRepository.cacheGeneration) { _ in
            if statusMessage != nil || !environment.networkMonitor.isOnline {
                applyLocalSummary()
            }
        }
    }

    private func refresh() async {
        loading = summary == nil
        statusMessage = nil
        defer { loading = false }
        do {
            summary = try await environment.reportsRepository.summary()
        } catch {
            applyLocalSummary()
            if error.isConnectivityError {
                statusMessage = tr("bets.offlineCached")
            } else if summary == nil {
                statusMessage = error.userMessage
            }
        }
    }

    private func applyLocalSummary() {
        let bets = environment.betsRepository.cachedBets()
        guard !bets.isEmpty else { return }
        summary = LocalBetFactory.summary(from: bets)
    }
}

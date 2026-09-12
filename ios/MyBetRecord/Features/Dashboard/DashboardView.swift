import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var summary: ReportSummary?
    @State private var loading = false
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("android.home")).font(.title2)
                Text(tr("android.summarySub")).foregroundStyle(.secondary)
                if let error { ErrorText(message: error) }
                if let summary {
                    let currency = summary.currency ?? summary.baseCurrency
                    MetricCard(label: tr("ticker.pl"), value: Formatters.money(summary.profit, currency: currency))
                    MetricCard(label: tr("android.turnover"), value: Formatters.money(summary.turnover, currency: currency))
                    MetricCard(label: tr("ticker.yield"), value: String(format: "%.2f%%", summary.yieldPct))
                    MetricCard(label: tr("reports.strikeRate"), value: String(format: "%.2f%%", summary.strikeRatePct))
                    MetricCard(label: tr("reports.totalBets"), value: "\(summary.settledBets) / \(summary.totalBets)")
                    if let bankroll = summary.bankroll {
                        MetricCard(label: tr("ticker.bankroll"), value: Formatters.money(bankroll, currency: summary.baseCurrency))
                    }
                } else if loading {
                    LoadingView()
                }
            }
            .padding()
        }
        .refreshable { await refresh() }
        .task { await refresh() }
    }

    private func refresh() async {
        loading = summary == nil
        error = nil
        defer { loading = false }
        do {
            summary = try await environment.reportsRepository.summary()
        } catch {
            self.error = error.userMessage
        }
    }
}

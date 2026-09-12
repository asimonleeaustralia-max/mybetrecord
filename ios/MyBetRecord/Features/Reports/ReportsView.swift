import SwiftUI
import Charts

struct ReportsView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var summary: ReportSummary?
    @State private var equity: [EquityPoint] = []
    @State private var monthly: [MonthlyProfit] = []
    @State private var loading = false
    @State private var exporting = false
    @State private var error: String?
    @State private var shareItems: [Any]?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("reports.title")).font(.title2)
                Text(tr("android.summarySub")).foregroundStyle(.secondary)
                if let error { ErrorText(message: error) }
                if let summary {
                    let currency = summary.currency ?? summary.baseCurrency
                    MetricCard(label: tr("reports.profitLoss"), value: Formatters.money(summary.profit, currency: currency))
                    MetricCard(label: tr("android.turnover"), value: Formatters.money(summary.turnover, currency: currency))
                    MetricCard(label: tr("reports.roi"), value: String(format: "%.2f%%", summary.roiPct))
                    MetricCard(label: tr("reports.yield"), value: String(format: "%.2f%%", summary.yieldPct))
                    MetricCard(label: tr("reports.strikeRate"), value: String(format: "%.2f%%", summary.strikeRatePct))
                }
                if equity.count >= 2 {
                    Text(tr("reports.equityCurve")).font(.headline)
                    Chart(equity) { point in
                        LineMark(
                            x: .value("Date", point.date),
                            y: .value("Cumulative", point.cumulative)
                        )
                    }
                    .frame(height: 200)
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                if !monthly.isEmpty {
                    Text(tr("reports.profitByMonth")).font(.headline)
                    Chart(monthly) { item in
                        BarMark(
                            x: .value("Month", item.month),
                            y: .value("Profit", item.profit)
                        )
                    }
                    .frame(height: 180)
                    .padding()
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
                Text(tr("android.exportShare")).font(.headline)
                HStack {
                    Button(tr("reports.exportCsv")) { export("csv", mime: "text/csv") }
                    Button(tr("reports.exportXlsx")) { export("xlsx", mime: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") }
                    Button(tr("reports.exportJson")) { export("json", mime: "application/json") }
                }
                .disabled(exporting)
            }
            .padding()
        }
        .refreshable { await refresh() }
        .task { await refresh() }
        .sheet(item: Binding(
            get: { shareItems.map { SharePayload(items: $0) } },
            set: { shareItems = $0?.items }
        )) { payload in
            ShareSheet(items: payload.items)
        }
    }

    private func refresh() async {
        loading = summary == nil
        error = nil
        defer { loading = false }
        do {
            async let summaryTask = environment.reportsRepository.summary()
            async let equityTask = environment.reportsRepository.equityCurve()
            let (s, e) = try await (summaryTask, equityTask)
            summary = s
            equity = e
            monthly = environment.reportsRepository.monthlyProfits(from: e)
        } catch {
            self.error = error.userMessage
        }
    }

    private func export(_ kind: String, mime: String) {
        exporting = true
        Task {
            defer { exporting = false }
            do {
                let data = try await environment.reportsRepository.export(kind: kind)
                let url = FileManager.default.temporaryDirectory.appendingPathComponent("mybetrecord-export.\(kind)")
                try data.write(to: url)
                shareItems = [url]
            } catch {
                self.error = error.userMessage
            }
        }
    }
}

private struct SharePayload: Identifiable {
    let id = UUID()
    let items: [Any]
}

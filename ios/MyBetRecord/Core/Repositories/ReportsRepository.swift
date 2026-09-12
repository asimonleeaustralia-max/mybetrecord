import Foundation

@MainActor
final class ReportsRepository {
    private let api: APIClient

    init(api: APIClient) {
        self.api = api
    }

    func summary() async throws -> ReportSummary {
        try await api.reportSummary()
    }

    func equityCurve() async throws -> [EquityPoint] {
        try await api.equityCurve()
    }

    func export(kind: String) async throws -> Data {
        try await api.exportReport(kind: kind)
    }

    func monthlyProfits(from equity: [EquityPoint]) -> [MonthlyProfit] {
        var buckets: [String: Double] = [:]
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        let monthFormatter = DateFormatter()
        monthFormatter.dateFormat = "MMM yyyy"
        for point in equity {
            guard let date = formatter.date(from: String(point.date.prefix(10))) else { continue }
            let key = monthFormatter.string(from: date)
            buckets[key, default: 0] += point.profit
        }
        return buckets.map { MonthlyProfit(id: $0.key, month: $0.key, profit: $0.value) }
            .sorted { $0.month < $1.month }
    }
}

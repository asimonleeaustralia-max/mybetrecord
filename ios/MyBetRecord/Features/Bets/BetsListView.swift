import SwiftUI

struct BetsListView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var bets: [Bet] = []
    @State private var refreshing = false
    @State private var error: String?
    @State private var pendingDelete: Bet?
    let onOpenBet: (String) -> Void

    var body: some View {
        Group {
            if bets.isEmpty && !refreshing {
                EmptyStateView(message: tr("bets.empty"))
            } else {
                List {
                    ForEach(bets) { bet in
                        Button { onOpenBet(bet.id) } label: {
                            BetRowView(bet: bet)
                        }
                        .swipeActions {
                            Button(role: .destructive) { pendingDelete = bet } label: {
                                Label(tr("common.confirm"), systemImage: "trash")
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle(tr("bets.title"))
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { onOpenBet("new") } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .refreshable { await refresh() }
        .task { await refresh() }
        .alert(tr("bets.deleteConfirm"), isPresented: Binding(
            get: { pendingDelete != nil },
            set: { if !$0 { pendingDelete = nil } }
        )) {
            Button(tr("common.confirm"), role: .destructive) {
                if let bet = pendingDelete { deleteBet(bet.id) }
                pendingDelete = nil
            }
            Button(tr("common.cancel"), role: .cancel) { pendingDelete = nil }
        } message: {
            if let bet = pendingDelete {
                Text("\(bet.event) / \(bet.selection)")
            }
        }
        if let error {
            Text(error).foregroundStyle(.red).padding()
        }
    }

    private func refresh() async {
        refreshing = true
        error = nil
        defer { refreshing = false }
        do {
            bets = try await environment.betsRepository.refreshBets()
        } catch {
            bets = (try? environment.betsRepository.cachedBets()) ?? []
            self.error = error.userMessage
        }
    }

    private func deleteBet(_ id: String) {
        Task {
            do {
                try await environment.betsRepository.deleteBet(id: id)
                bets.removeAll { $0.id == id }
            } catch {
                self.error = error.userMessage
            }
        }
    }
}

struct BetRowView: View {
    let bet: Bet

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(bet.event).font(.headline)
            Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            Text(detail).font(.caption).foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private var subtitle: String {
        var parts = [bet.selection, bet.sport, tr("outcomes.\(bet.outcome)")]
        if bet.isMultiple { parts.append(tr("bets.legsCount", params: ["count": "\(bet.legs.count)"])) }
        if bet.freeBet { parts.append(tr("form.freeBetBadge")) }
        return parts.joined(separator: " · ")
    }

    private var detail: String {
        var parts = [
            "\(tr("bets.odds")) \(bet.oddsDecimal)",
            "\(tr("form.stake")) \(Formatters.money(bet.stake, currency: bet.currency))",
            "\(tr("bets.pl")) \(Formatters.money(bet.profit, currency: bet.currency))",
        ]
        if let clv = bet.clvPct {
            parts.append("\(tr("bets.clv")) \(String(format: "%.2f", clv))%")
        }
        return parts.joined(separator: " · ")
    }
}

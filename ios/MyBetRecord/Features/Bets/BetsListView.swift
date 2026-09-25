import SwiftUI

struct BetsListView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var bets: [Bet] = []
    @State private var refreshing = false
    @State private var statusMessage: String?
    @State private var pendingDelete: Bet?
    let onOpenBet: (String) -> Void

    var body: some View {
        Group {
            if bets.isEmpty && !refreshing {
                EmptyStateView(message: tr("bets.empty"))
            } else {
                List {
                    if let statusMessage {
                        Text(statusMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .listRowBackground(Color.clear)
                    }
                    ForEach(bets) { bet in
                        Button { onOpenBet(bet.id) } label: {
                            BetRowView(
                                bet: bet,
                                isPendingSync: environment.betsRepository.isPendingSync(id: bet.id)
                            )
                        }
                        .swipeActions {
                            Button(role: .destructive) { pendingDelete = bet } label: {
                                Label(tr("common.delete"), systemImage: "trash")
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
        .onChange(of: environment.betsRepository.cacheGeneration) { _ in
            bets = environment.betsRepository.cachedBets()
            updateStatusMessage()
        }
        .onChange(of: environment.betsRepository.pendingSyncCount) { _ in
            updateStatusMessage()
        }
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
    }

    private func refresh() async {
        refreshing = true
        defer { refreshing = false }
        // Show cache immediately so offline launches aren't blank.
        bets = environment.betsRepository.cachedBets()
        updateStatusMessage()
        do {
            bets = try await environment.betsRepository.refreshBets()
            updateStatusMessage()
        } catch {
            bets = environment.betsRepository.cachedBets()
            if error.isConnectivityError {
                statusMessage = tr("bets.offlineCached")
            } else {
                statusMessage = error.userMessage
            }
        }
    }

    private func updateStatusMessage() {
        let pending = environment.betsRepository.pendingSyncCount
        if pending > 0 {
            statusMessage = tr("bets.pendingSync", params: ["count": "\(pending)"])
        } else if !environment.networkMonitor.isOnline {
            statusMessage = tr("bets.offlineCached")
        } else {
            statusMessage = nil
        }
    }

    private func deleteBet(_ id: String) {
        Task {
            do {
                try await environment.betsRepository.deleteBet(id: id)
                bets.removeAll { $0.id == id }
                updateStatusMessage()
            } catch {
                statusMessage = error.userMessage
            }
        }
    }
}

struct BetRowView: View {
    let bet: Bet
    var isPendingSync = false

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(bet.event).font(.headline)
                if isPendingSync {
                    Text(tr("bets.pendingBadge"))
                        .font(.caption2.weight(.semibold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.orange.opacity(0.15), in: Capsule())
                        .foregroundStyle(.orange)
                }
            }
            Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            Text(detail).font(.caption).foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private var subtitle: String {
        var parts = [bet.selection, bet.sport, tr("outcomes.\(bet.outcome)")]
        if bet.side == "lay" { parts.append(tr("form.sideLay")) }
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

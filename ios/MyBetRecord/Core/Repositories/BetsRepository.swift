import Foundation

@MainActor
final class BetsRepository: ObservableObject {
    private let api: APIClient
    private let cacheStorage: BetCacheStorage

    init(api: APIClient, cacheStorage: BetCacheStorage) {
        self.api = api
        self.cacheStorage = cacheStorage
    }

    func cachedBets() throws -> [Bet] {
        return cacheStorage.fetch()
            .sorted { $0.placedAt > $1.placedAt }
            .compactMap(BetCacheCodec.decode)
    }

    func refreshBets() async throws -> [Bet] {
        let remote = try await api.listBets()
        try upsertAll(remote)
        return remote
    }

    func getBet(id: String) async throws -> Bet {
        do {
            let remote = try await api.getBet(id: id)
            try upsert(remote)
            return remote
        } catch {
            if let cached = try cachedBets().first(where: { $0.id == id }) {
                return cached
            }
            throw error
        }
    }

    func createBet(_ body: BetCreate) async throws -> Bet {
        let created = try await api.createBet(body)
        try upsert(created)
        return created
    }

    func updateBet(id: String, body: BetUpdate) async throws -> Bet {
        let updated = try await api.updateBet(id: id, body: body)
        try upsert(updated)
        return updated
    }

    func deleteBet(id: String) async throws {
        try await api.deleteBet(id: id)
        if let entity = cacheStorage.fetch(id: id) {
            cacheStorage.delete(entity)
        }
    }

    func createShareLink(id: String) async throws -> String {
        let share = try await api.createShareLink(id: id)
        try? await refreshCachedBet(id: id)
        return share.shareToken
    }

    func revokeShareLink(id: String) async throws {
        try await api.revokeShareLink(id: id)
        try? await refreshCachedBet(id: id)
    }

    private func refreshCachedBet(id: String) async throws {
        let remote = try await api.getBet(id: id)
        try upsert(remote)
    }

    private func upsertAll(_ bets: [Bet]) throws {
        for bet in bets {
            try upsert(bet)
        }
    }

    private func upsert(_ bet: Bet) throws {
        let entity = try BetCacheCodec.encode(bet)
        cacheStorage.insert(entity)
    }
}

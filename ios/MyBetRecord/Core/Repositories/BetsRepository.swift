import Foundation

@MainActor
final class BetsRepository: ObservableObject {
    private let api: APIClient
    private let cacheStorage: BetCacheStorage
    private let outbox: SyncOutbox

    @Published private(set) var pendingSyncCount = 0
    @Published private(set) var isSyncing = false
    @Published private(set) var cacheGeneration = 0
    @Published private(set) var lastSyncError: String?

    private var syncTask: Task<Void, Never>?

    init(api: APIClient, cacheStorage: BetCacheStorage, outbox: SyncOutbox) {
        self.api = api
        self.cacheStorage = cacheStorage
        self.outbox = outbox
        pendingSyncCount = outbox.pendingCount
    }

    func cachedBets() -> [Bet] {
        cacheStorage.fetch()
            .sorted { $0.placedAt > $1.placedAt }
            .compactMap(BetCacheCodec.decode)
    }

    func isPendingSync(id: String) -> Bool {
        outbox.all.contains { $0.localBetId == id }
    }

    /// Pull from the server when possible; always preserve unsynced local changes.
    func refreshBets() async throws -> [Bet] {
        await syncPending()
        do {
            let remote = try await api.listBets()
            try mergeRemote(remote)
            bumpCache()
            return cachedBets()
        } catch {
            if error.isConnectivityError {
                return cachedBets()
            }
            throw error
        }
    }

    func getBet(id: String) async throws -> Bet {
        if let cached = cachedBets().first(where: { $0.id == id }) {
            if !LocalBetFactory.isLocalId(id), !isPendingSync(id: id) {
                Task { try? await refreshCachedBet(id: id) }
            }
            return cached
        }
        let remote = try await api.getBet(id: id)
        try upsert(remote)
        bumpCache()
        return remote
    }

    func createBet(_ body: BetCreate) async throws -> Bet {
        let localId = LocalBetFactory.localId()
        let local = LocalBetFactory.make(from: body, id: localId)
        try upsert(local)
        bumpCache()

        do {
            let created = try await api.createBet(body)
            if let entity = cacheStorage.fetch(id: localId) {
                cacheStorage.delete(entity)
            }
            try upsert(created)
            bumpCache()
            return created
        } catch {
            guard error.isConnectivityError else {
                if let entity = cacheStorage.fetch(id: localId) {
                    cacheStorage.delete(entity)
                }
                bumpCache()
                throw error
            }
            try outbox.enqueueCreate(localBetId: localId, body: body)
            publishOutbox()
            scheduleSync()
            return local
        }
    }

    func updateBet(id: String, body: BetUpdate) async throws -> Bet {
        let existing = cachedBets().first(where: { $0.id == id })
        let optimistic = existing.map { LocalBetFactory.apply(update: body, to: $0) }
        if let optimistic {
            try upsert(optimistic)
            bumpCache()
        }

        // Still-buffered create: fold the edit into the outbox and stay offline-safe.
        if outbox.pendingCreateIds().contains(id) {
            try outbox.enqueueUpdate(localBetId: id, body: body)
            publishOutbox()
            scheduleSync()
            if let optimistic { return optimistic }
            throw APIError.offline(message: "Bet isn't available offline yet. Connect once to open it, then you can edit offline.")
        }

        do {
            let updated = try await api.updateBet(id: id, body: body)
            try upsert(updated)
            bumpCache()
            return updated
        } catch {
            guard error.isConnectivityError else {
                // Roll back optimistic cache entry if we still have the pre-edit copy.
                if let existing {
                    try? upsert(existing)
                    bumpCache()
                }
                throw error
            }
            guard optimistic != nil || existing != nil else {
                throw APIError.offline(message: "Bet isn't available offline yet. Connect once to open it, then you can edit offline.")
            }
            try outbox.enqueueUpdate(localBetId: id, body: body)
            publishOutbox()
            scheduleSync()
            return optimistic!
        }
    }

    func deleteBet(id: String) async throws {
        let removedEntity = cacheStorage.fetch(id: id)
        if let removedEntity {
            cacheStorage.delete(removedEntity)
            bumpCache()
        }

        // Unsynced local create — just drop it from the outbox.
        if outbox.pendingCreateIds().contains(id) {
            outbox.enqueueDelete(localBetId: id)
            publishOutbox()
            return
        }

        do {
            try await api.deleteBet(id: id)
            outbox.cancelPendingMutations(localBetId: id)
            publishOutbox()
        } catch {
            guard error.isConnectivityError else {
                if let removedEntity {
                    cacheStorage.insert(removedEntity)
                    bumpCache()
                }
                throw error
            }
            outbox.enqueueDelete(localBetId: id)
            publishOutbox()
            scheduleSync()
        }
    }

    func createShareLink(id: String) async throws -> String {
        if LocalBetFactory.isLocalId(id) || isPendingSync(id: id) {
            throw APIError.offline(message: "Share links need a connection. Sync this bet first, then try again.")
        }
        let share = try await api.createShareLink(id: id)
        try? await refreshCachedBet(id: id)
        bumpCache()
        return share.shareToken
    }

    func revokeShareLink(id: String) async throws {
        try await api.revokeShareLink(id: id)
        try? await refreshCachedBet(id: id)
        bumpCache()
    }

    func listSports() async throws -> [String] {
        try await api.listSports()
    }

    func listBetTypes() async throws -> [String] {
        try await api.listBetTypes()
    }

    func scheduleSync() {
        syncTask?.cancel()
        syncTask = Task { await syncPending() }
    }

    func syncPending() async {
        guard !isSyncing else { return }
        let pending = outbox.all.sorted { $0.createdAt < $1.createdAt }
        guard !pending.isEmpty else {
            publishOutbox()
            return
        }

        isSyncing = true
        lastSyncError = nil
        defer {
            isSyncing = false
            publishOutbox()
        }

        for op in pending {
            if Task.isCancelled { break }
            do {
                try await apply(op)
                outbox.remove(op)
            } catch {
                if error.isConnectivityError {
                    lastSyncError = nil
                    break
                }
                if let apiError = error as? APIError, case .unauthorized = apiError {
                    lastSyncError = apiError.errorDescription
                    break
                }
                outbox.markFailure(op, error: error.userMessage)
                lastSyncError = error.userMessage
                continue
            }
        }
        bumpCache()
    }

    func clearLocalData() {
        cacheStorage.deleteAll()
        outbox.clear()
        pendingSyncCount = 0
        lastSyncError = nil
        bumpCache()
    }

    private func apply(_ op: PendingSyncOp) async throws {
        switch op.kind {
        case .create:
            let body = try outbox.decodeCreate(op)
            let created = try await api.createBet(body)
            if let entity = cacheStorage.fetch(id: op.localBetId) {
                cacheStorage.delete(entity)
            }
            try upsert(created)
            outbox.remapBetId(from: op.localBetId, to: created.id)

        case .update:
            let body = try outbox.decodeUpdate(op)
            let updated = try await api.updateBet(id: op.localBetId, body: body)
            try upsert(updated)

        case .delete:
            do {
                try await api.deleteBet(id: op.localBetId)
            } catch let APIError.http(status, _) where status == 404 {
                // Already gone on server.
            }
            if let entity = cacheStorage.fetch(id: op.localBetId) {
                cacheStorage.delete(entity)
            }
        }
    }

    private func mergeRemote(_ remote: [Bet]) throws {
        let pendingCreates = outbox.pendingCreateIds()
        let pendingDeletes = outbox.pendingDeleteIds()
        let pendingUpdates = outbox.pendingUpdateIds()
        let localById = Dictionary(uniqueKeysWithValues: cachedBets().map { ($0.id, $0) })
        let localOnly = cachedBets().filter { pendingCreates.contains($0.id) }

        cacheStorage.deleteAll()

        for bet in remote {
            if pendingDeletes.contains(bet.id) { continue }
            if pendingUpdates.contains(bet.id), let local = localById[bet.id] {
                try upsert(local)
            } else {
                try upsert(bet)
            }
        }
        for bet in localOnly {
            try upsert(bet)
        }
    }

    private func refreshCachedBet(id: String) async throws {
        let remote = try await api.getBet(id: id)
        try upsert(remote)
        bumpCache()
    }

    private func upsert(_ bet: Bet) throws {
        let entity = try BetCacheCodec.encode(bet)
        cacheStorage.insert(entity)
    }

    private func publishOutbox() {
        pendingSyncCount = outbox.pendingCount
    }

    private func bumpCache() {
        cacheGeneration &+= 1
    }
}

import Foundation

enum SyncOpKind: String, Codable {
    case create
    case update
    case delete
}

struct PendingSyncOp: Codable, Identifiable, Equatable {
    let id: String
    var localBetId: String
    var kind: SyncOpKind
    var createPayloadJSON: String?
    var updatePayloadJSON: String?
    var createdAt: Date
    var attemptCount: Int
    var lastError: String?

    init(
        id: String = UUID().uuidString,
        localBetId: String,
        kind: SyncOpKind,
        createPayloadJSON: String? = nil,
        updatePayloadJSON: String? = nil,
        createdAt: Date = Date(),
        attemptCount: Int = 0,
        lastError: String? = nil
    ) {
        self.id = id
        self.localBetId = localBetId
        self.kind = kind
        self.createPayloadJSON = createPayloadJSON
        self.updatePayloadJSON = updatePayloadJSON
        self.createdAt = createdAt
        self.attemptCount = attemptCount
        self.lastError = lastError
    }
}

/// Durable queue of bet mutations waiting to reach the server.
@MainActor
final class SyncOutbox {
    private let fileURL: URL
    private var ops: [PendingSyncOp] = []
    private let encoder = JSONEncoder.api
    private let decoder = JSONDecoder.api

    init() {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        fileURL = documents.appendingPathComponent("bet_sync_outbox.json")
        load()
    }

    var pendingCount: Int { ops.count }

    var all: [PendingSyncOp] { ops }

    func pendingCreateIds() -> Set<String> {
        Set(ops.filter { $0.kind == .create }.map(\.localBetId))
    }

    func pendingDeleteIds() -> Set<String> {
        Set(ops.filter { $0.kind == .delete }.map(\.localBetId))
    }

    func pendingUpdateIds() -> Set<String> {
        Set(ops.filter { $0.kind == .update }.map(\.localBetId))
    }

    func enqueueCreate(localBetId: String, body: BetCreate) throws {
        let json = try encode(body)
        ops.append(PendingSyncOp(localBetId: localBetId, kind: .create, createPayloadJSON: json))
        save()
    }

    /// Fold an edit into a still-unsynced create, or merge/replace a pending update.
    func enqueueUpdate(localBetId: String, body: BetUpdate) throws {
        if let idx = ops.firstIndex(where: { $0.localBetId == localBetId && $0.kind == .create }),
           let createJSON = ops[idx].createPayloadJSON,
           var create = try? decoder.decode(BetCreate.self, from: Data(createJSON.utf8)) {
            create = merge(update: body, into: create)
            ops[idx].createPayloadJSON = try encode(create)
            ops[idx].lastError = nil
            save()
            return
        }

        if let idx = ops.firstIndex(where: { $0.localBetId == localBetId && $0.kind == .update }),
           let updateJSON = ops[idx].updatePayloadJSON,
           var existing = try? decoder.decode(BetUpdate.self, from: Data(updateJSON.utf8)) {
            existing = merge(update: body, into: existing)
            ops[idx].updatePayloadJSON = try encode(existing)
            ops[idx].lastError = nil
            save()
            return
        }

        ops.append(PendingSyncOp(
            localBetId: localBetId,
            kind: .update,
            updatePayloadJSON: try encode(body)
        ))
        save()
    }

    func enqueueDelete(localBetId: String) {
        // Unsynced create: drop create/update ops and skip the server call.
        if ops.contains(where: { $0.localBetId == localBetId && $0.kind == .create }) {
            ops.removeAll { $0.localBetId == localBetId }
            save()
            return
        }
        ops.removeAll { $0.localBetId == localBetId && ($0.kind == .update || $0.kind == .delete) }
        ops.append(PendingSyncOp(localBetId: localBetId, kind: .delete))
        save()
    }

    /// Drop queued updates for a bet after a successful online delete (no server delete needed).
    func cancelPendingMutations(localBetId: String) {
        ops.removeAll { $0.localBetId == localBetId }
        save()
    }

    func decodeCreate(_ op: PendingSyncOp) throws -> BetCreate {
        guard let json = op.createPayloadJSON, let data = json.data(using: .utf8) else {
            throw SyncOutboxError.missingPayload
        }
        return try decoder.decode(BetCreate.self, from: data)
    }

    func decodeUpdate(_ op: PendingSyncOp) throws -> BetUpdate {
        guard let json = op.updatePayloadJSON, let data = json.data(using: .utf8) else {
            throw SyncOutboxError.missingPayload
        }
        return try decoder.decode(BetUpdate.self, from: data)
    }

    func remove(_ op: PendingSyncOp) {
        ops.removeAll { $0.id == op.id }
        save()
    }

    func markFailure(_ op: PendingSyncOp, error: String) {
        guard let idx = ops.firstIndex(where: { $0.id == op.id }) else { return }
        ops[idx].attemptCount += 1
        ops[idx].lastError = error
        save()
    }

    func remapBetId(from oldId: String, to newId: String) {
        for i in ops.indices where ops[i].localBetId == oldId {
            ops[i].localBetId = newId
        }
        save()
    }

    func clear() {
        ops.removeAll()
        save()
    }

    private func encode<T: Encodable>(_ value: T) throws -> String {
        let data = try encoder.encode(value)
        guard let json = String(data: data, encoding: .utf8) else {
            throw SyncOutboxError.missingPayload
        }
        return json
    }

    private func load() {
        guard FileManager.default.fileExists(atPath: fileURL.path),
              let data = try? Data(contentsOf: fileURL) else {
            return
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        guard let decoded = try? decoder.decode([PendingSyncOp].self, from: data) else { return }
        ops = decoded
    }

    private func save() {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        guard let data = try? encoder.encode(ops) else { return }
        try? data.write(to: fileURL, options: .atomic)
    }

    private func merge(update: BetUpdate, into create: BetCreate) -> BetCreate {
        BetCreate(
            sport: update.sport ?? create.sport,
            event: update.event ?? create.event,
            selection: update.selection ?? create.selection,
            odds: update.odds ?? create.odds,
            stake: update.stake ?? create.stake,
            betType: update.betType ?? create.betType,
            side: update.side ?? create.side,
            currency: update.currency ?? create.currency,
            oddsFormat: update.oddsFormat ?? create.oddsFormat,
            oddsDenominator: update.oddsDenominator ?? create.oddsDenominator,
            outcome: update.outcome ?? create.outcome,
            tournament: update.tournament ?? create.tournament,
            bookmaker: update.bookmaker ?? create.bookmaker,
            portal: update.portal ?? create.portal,
            exchangeCommissionPct: update.exchangeCommissionPct ?? create.exchangeCommissionPct,
            tipster: update.tipster ?? create.tipster,
            betBroker: update.betBroker ?? create.betBroker,
            notes: update.notes ?? create.notes,
            eachWay: update.eachWay ?? create.eachWay,
            placeFraction: update.placeFraction ?? create.placeFraction,
            placed: update.placed ?? create.placed,
            freeBet: update.freeBet ?? create.freeBet,
            isMultiple: update.isMultiple ?? create.isMultiple,
            legs: update.legs ?? create.legs,
            cashOutAmount: update.cashOutAmount ?? create.cashOutAmount,
            betModel: update.betModel ?? create.betModel,
            modelImpliedOdds: update.modelImpliedOdds ?? create.modelImpliedOdds,
            personalImpliedOdds: update.personalImpliedOdds ?? create.personalImpliedOdds,
            tipsterImpliedOdds: update.tipsterImpliedOdds ?? create.tipsterImpliedOdds,
            closingOdds: update.closingOdds ?? create.closingOdds,
            closingOddsExchange: update.closingOddsExchange ?? create.closingOddsExchange,
            placedAt: update.placedAt ?? create.placedAt,
            eventAt: update.eventAt ?? create.eventAt,
            settledAt: update.settledAt ?? create.settledAt
        )
    }

    private func merge(update: BetUpdate, into existing: BetUpdate) -> BetUpdate {
        var merged = existing
        if let v = update.sport { merged.sport = v }
        if let v = update.event { merged.event = v }
        if let v = update.selection { merged.selection = v }
        if let v = update.odds { merged.odds = v }
        if let v = update.stake { merged.stake = v }
        if let v = update.betType { merged.betType = v }
        if let v = update.side { merged.side = v }
        if let v = update.currency { merged.currency = v }
        if let v = update.oddsFormat { merged.oddsFormat = v }
        if let v = update.oddsDenominator { merged.oddsDenominator = v }
        if let v = update.outcome { merged.outcome = v }
        if let v = update.tournament { merged.tournament = v }
        if let v = update.bookmaker { merged.bookmaker = v }
        if let v = update.portal { merged.portal = v }
        if let v = update.exchangeCommissionPct { merged.exchangeCommissionPct = v }
        if let v = update.tipster { merged.tipster = v }
        if let v = update.betBroker { merged.betBroker = v }
        if let v = update.notes { merged.notes = v }
        if let v = update.eachWay { merged.eachWay = v }
        if let v = update.placeFraction { merged.placeFraction = v }
        if let v = update.placed { merged.placed = v }
        if let v = update.freeBet { merged.freeBet = v }
        if let v = update.isMultiple { merged.isMultiple = v }
        if let v = update.legs { merged.legs = v }
        if let v = update.cashOutAmount { merged.cashOutAmount = v }
        if let v = update.betModel { merged.betModel = v }
        if let v = update.modelImpliedOdds { merged.modelImpliedOdds = v }
        if let v = update.personalImpliedOdds { merged.personalImpliedOdds = v }
        if let v = update.tipsterImpliedOdds { merged.tipsterImpliedOdds = v }
        if let v = update.closingOdds { merged.closingOdds = v }
        if let v = update.closingOddsExchange { merged.closingOddsExchange = v }
        if let v = update.eventAt { merged.eventAt = v }
        if let v = update.placedAt { merged.placedAt = v }
        if let v = update.settledAt { merged.settledAt = v }
        return merged
    }
}

enum SyncOutboxError: LocalizedError {
    case missingPayload

    var errorDescription: String? {
        switch self {
        case .missingPayload: return "Sync payload missing"
        }
    }
}

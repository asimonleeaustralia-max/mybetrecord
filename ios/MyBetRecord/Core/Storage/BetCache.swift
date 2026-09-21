import Foundation

// iOS 15 compatible cache storage using FileManager
final class BetCacheEntity: Codable {
    var id: String
    var event: String
    var selection: String
    var sport: String
    var betType: String
    var oddsDecimal: Double
    var stake: Double
    var currency: String
    var outcome: String
    var profit: Double
    var placedAt: String
    var bookmaker: String?
    var payloadJson: String

    init(
        id: String,
        event: String,
        selection: String,
        sport: String,
        betType: String,
        oddsDecimal: Double,
        stake: Double,
        currency: String,
        outcome: String,
        profit: Double,
        placedAt: String,
        bookmaker: String?,
        payloadJson: String
    ) {
        self.id = id
        self.event = event
        self.selection = selection
        self.sport = sport
        self.betType = betType
        self.oddsDecimal = oddsDecimal
        self.stake = stake
        self.currency = currency
        self.outcome = outcome
        self.profit = profit
        self.placedAt = placedAt
        self.bookmaker = bookmaker
        self.payloadJson = payloadJson
    }
}

// Simple file-based storage for iOS 15 compatibility
@MainActor
final class BetCacheStorage {
    private let fileURL: URL
    private var cache: [String: BetCacheEntity] = [:]
    
    init() {
        let documentsDirectory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        fileURL = documentsDirectory.appendingPathComponent("bet_cache.json")
        loadCache()
    }
    
    private func loadCache() {
        guard FileManager.default.fileExists(atPath: fileURL.path),
              let data = try? Data(contentsOf: fileURL),
              let entities = try? JSONDecoder().decode([BetCacheEntity].self, from: data) else {
            return
        }
        cache = Dictionary(uniqueKeysWithValues: entities.map { ($0.id, $0) })
    }
    
    private func saveCache() {
        let entities = Array(cache.values)
        guard let data = try? JSONEncoder().encode(entities) else { return }
        try? data.write(to: fileURL)
    }
    
    func insert(_ entity: BetCacheEntity) {
        cache[entity.id] = entity
        saveCache()
    }
    
    func delete(_ entity: BetCacheEntity) {
        cache.removeValue(forKey: entity.id)
        saveCache()
    }
    
    func fetch() -> [BetCacheEntity] {
        Array(cache.values)
    }
    
    func fetch(id: String) -> BetCacheEntity? {
        cache[id]
    }
    
    func deleteAll() {
        cache.removeAll()
        saveCache()
    }
}

enum BetCacheCodec {
    private static let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    private static let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    static func encode(_ bet: Bet) throws -> BetCacheEntity {
        let data = try encoder.encode(bet)
        let json = String(data: data, encoding: .utf8) ?? "{}"
        return BetCacheEntity(
            id: bet.id,
            event: bet.event,
            selection: bet.selection,
            sport: bet.sport,
            betType: bet.betType,
            oddsDecimal: bet.oddsDecimal,
            stake: bet.stake,
            currency: bet.currency,
            outcome: bet.outcome,
            profit: bet.profit,
            placedAt: bet.placedAt,
            bookmaker: bet.bookmaker,
            payloadJson: json
        )
    }

    static func decode(_ entity: BetCacheEntity) -> Bet? {
        guard let data = entity.payloadJson.data(using: .utf8),
              let bet = try? decoder.decode(Bet.self, from: data) else {
            return Bet(
                id: entity.id,
                event: entity.event,
                selection: entity.selection,
                sport: entity.sport,
                betType: entity.betType,
                oddsDecimal: entity.oddsDecimal,
                stake: entity.stake,
                currency: entity.currency,
                outcome: entity.outcome,
                profit: entity.profit,
                placedAt: entity.placedAt,
                bookmaker: entity.bookmaker
            )
        }
        return bet
    }
}

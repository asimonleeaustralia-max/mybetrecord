import Foundation

/// Predefined suggestion lists mirrored from the web app (`frontend/src/app.js`).
/// Fields remain free-text; these are convenience suggestions only.
enum BetCatalog {
    static let sports: [String] = [
        // Major markets
        "Soccer", "Horse racing", "American football", "Basketball", "Tennis",
        "Cricket", "Golf", "Baseball", "Rugby union", "Ice hockey",
        "Boxing", "MMA", "Greyhound racing", "Harness racing", "Darts",
        "Snooker", "Rugby league", "Rugby sevens", "Cycling", "Formula 1",
        "Esports", "Volleyball", "Handball", "Table tennis", "Futsal",
        // Regional & secondary team sports
        "Australian rules football", "Gaelic football", "Hurling", "Field hockey",
        "Beach volleyball", "Water polo", "Lacrosse", "Floorball", "Netball",
        "Bandy", "Softball", "Kabaddi",
        // Motorsport
        "Motorsport", "NASCAR", "MotoGP", "IndyCar", "Rally",
        // Winter sports
        "Alpine skiing", "Cross-country skiing", "Ski jumping", "Biathlon",
        "Curling", "Figure skating", "Bobsleigh", "Luge", "Skeleton",
        // Combat & racket
        "Muay Thai", "Kickboxing", "Wrestling", "Pro wrestling", "Badminton",
        "Squash", "Padel", "Pickleball",
        // Athletics & aquatics
        "Athletics", "Swimming", "Diving", "Triathlon", "Rowing", "Sailing",
        "Surfing", "Skateboarding", "Climbing", "Gymnastics",
        // Other sports & games
        "Pool", "Bowls", "Chess", "Equestrian", "Polo", "Shooting", "Archery",
        // Non-sport / specials
        "Virtual sports", "Olympics", "Politics", "Entertainment", "TV & film",
        "Music awards", "Financial markets", "Lottery", "Specials",
    ]

    static let betTypes: [String] = [
        // Match result
        "Win", "Each way", "Place", "Outright", "Ante-post", "Draw no bet", "Double chance",
        "Match odds", "Moneyline", "To qualify", "To be relegated", "Top scorer",
        // Handicap & spread
        "Handicap", "Asian handicap", "European handicap", "Spread", "Puck line", "Run line",
        "Game handicap", "Set handicap",
        // Totals
        "Over / Under", "Asian totals", "Team totals", "Total goals", "Total points",
        "Total games", "Total sets", "Total runs", "Total corners", "Total cards",
        // Accumulators & full cover
        "Accumulator", "Multi / Acca", "Parlay", "Full cover", "System bet",
        "Double", "Treble", "Trixie", "Patent", "Yankee", "Canadian", "Heinz",
        "Super Heinz", "Goliath", "Lucky 15", "Lucky 31", "Lucky 63", "Alphabet",
        // Score & time
        "Correct score", "Half-time / Full-time", "Half-time result", "Full-time result",
        "Winning margin", "Race to points", "Next goal", "Next scorer",
        // Goals & scoring
        "Both teams to score", "Clean sheet", "First goalscorer", "Anytime goalscorer",
        "Last goalscorer", "To score", "Goal line", "Odd / Even goals",
        // Tennis & racket
        "Set betting", "Set winner", "Game winner", "Total aces",
        // Racing
        "Forecast", "Tricast", "Reverse forecast", "Without favourite", "Match bet",
        "Distance", "Faller insurance",
        // Props & specials
        "Prop", "Player prop", "Team prop", "Special", "Method of victory", "Round betting",
        "Cards", "Corners", "Penalties", "Bookings", "Shots on target",
        "First team to score", "Highest scoring half", "Win to nil",
        // Exchange & trading
        "Back", "Lay", "Trading",
        // Other
        "In-play", "Cash out", "Boosted odds", "Request a bet", "Same game parlay",
        "Bet builder", "Insurance", "Free bet",
    ]

    static let bookmakers: [String] = [
        // Global / multi-market operators
        "Bet365", "FanDuel", "DraftKings", "BetMGM", "Caesars Sportsbook",
        "Betway", "Paddy Power", "Betfair", "Sky Bet", "William Hill",
        "Ladbrokes", "Coral", "bwin", "Unibet", "888sport",
        "Betsson", "Pinnacle", "Stake", "Betano", "Tipico",
        "Betfred", "BetVictor", "Spreadex", "BoyleSports", "QuinnBet",
        "Virgin Bet", "LiveScore Bet", "Novibet", "Coolbet", "ComeOn",
        "LeoVegas", "Mr Green", "PlayOJO", "Grosvenor", "NordicBet",
        "Betsafe", "Expekt", "Rizk", "Betclic", "Winamax",
        "Sisal", "GoldBet", "Lottomatica", "Snai", "Eurobet",
        "Planetwin365", "Codere", "OPAP", "Fortuna", "Superbet",
        "Mozzart Bet", "STS", "OlyBet", "Optibet", "TonyBet",
        "Marathonbet", "Interwetten", "Admiral", "Cashpoint", "Bet3000",
        "Merkur Bets", "Happybet", "NetBet", "ZEbet", "PMU",
        "Parions Sport", "FDJ", "Svenska Spel", "ATG", "Danske Spil",
        "LOTTO24", "Lottoland", "GGPoker", "BetKing", "Hollywoodbets",
        "1xBet", "22Bet", "Melbet", "Dafabet", "SBOBET",
        "188Bet", "M88", "W88", "Fun88", "12Bet",
        // US & Canada sportsbooks
        "Fanatics Sportsbook", "BetRivers", "Hard Rock Bet", "theScore Bet", "ESPN BET",
        "PointsBet", "Bally Bet", "WynnBET", "SugarHouse", "SuperBook",
        "Circa Sports", "BetOnline", "Bovada", "MyBookie", "BetUS",
        "BetOnline.ag", "Sports Interaction", "Bet99", "Proline+", "PlayUp",
        "Underdog Sportsbook", "Fliff", "Rebet", "Golden Nugget", "Horseshoe",
        // Australia & New Zealand
        "Sportsbet", "TAB", "TAB NZ", "Neds", "BetRight",
        "PointsBet AU", "BlueBet", "TopSport", "Palmerbet", "BetDeluxe",
        "Ladbrokes AU", "Unibet AU",
        // Latin America
        "Caliente", "Betcris", "Rivalo", "Betplay", "Rushbet",
        "Betwarrior", "Pixbet", "EstrelaBet", "KTO", "Betnacional",
        "Sportingbet", "Blaze",
        // Asia-Pacific state & racing
        "HKJC", "Singapore Pools",
        // UK & Ireland independents
        "AK Bets", "Star Sports", "McBookie", "Jennings Bet", "BetGoodwin",
        "PricedUp", "talkSPORT BET", "Betzone", "DragonBet", "VBet",
        "10bet", "SBK", "Marshalls World of Sport",
        // Africa
        "Supabets", "World Sports Betting", "Sunbet", "Gbets", "Bet.co.za",
        // Betting exchanges
        "Betfair Exchange", "Smarkets", "Matchbook", "Betdaq", "SX Bet",
        "Prophet Exchange", "Sporttrade", "Novig", "SportX", "Orbit Exchange",
        "Betconnect",
        // Prediction markets
        "Kalshi", "Polymarket", "PredictIt",
    ]

    /// Merge extras (e.g. previously used values) ahead of the catalog, case-insensitive dedupe.
    static func choices(catalog: [String], extras: [String] = []) -> [String] {
        var seen = Set<String>()
        var items: [String] = []
        for value in extras + catalog {
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            let key = trimmed.lowercased()
            guard !key.isEmpty, !seen.contains(key) else { continue }
            seen.insert(key)
            items.append(trimmed)
        }
        return items.sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }
}

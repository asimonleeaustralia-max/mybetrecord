import Foundation

@MainActor
final class I18n: ObservableObject {
    static let shared = I18n()

    @Published private(set) var locale: String = "en"
    private var tables: [String: [String: Any]] = [:]
    private(set) var languages: [(code: String, label: String)] = []

    private init() {
        loadLanguagesManifest()
        let initial = AppPreferences.locale ?? Locale.current.language.languageCode?.identifier ?? "en"
        switchLocale(Self.normalize(initial) ?? "en")
    }

    func switchLocale(_ code: String) {
        let normalized = Self.normalize(code) ?? "en"
        locale = normalized
        if tables[normalized] == nil {
            tables[normalized] = loadTable(normalized) ?? loadTable("en") ?? [:]
        }
        objectWillChange.send()
    }

    func tr(_ key: String, params: [String: String] = [:]) -> String {
        let value = lookup(key, in: tables[locale] ?? [:]) ?? lookup(key, in: tables["en"] ?? [:]) ?? key
        return interpolate(value, params: params)
    }

    static func normalize(_ code: String) -> String? {
        let trimmed = code.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return nil }
        if Bundle.main.url(forResource: trimmed, withExtension: "json", subdirectory: "Locales") != nil {
            return trimmed
        }
        let base = trimmed.split(separator: "-").first.map(String.init) ?? trimmed
        if Bundle.main.url(forResource: base, withExtension: "json", subdirectory: "Locales") != nil {
            return base
        }
        return "en"
    }

    private func loadLanguagesManifest() {
        guard let url = Bundle.main.url(forResource: "languages", withExtension: "json", subdirectory: "Locales"),
              let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let all = json["all"] as? [String: String] else {
            languages = [("en", "English")]
            return
        }
        languages = all.keys.sorted().map { ($0, all[$0] ?? $0) }
    }

    private func loadTable(_ code: String) -> [String: Any]? {
        guard let url = Bundle.main.url(forResource: code, withExtension: "json", subdirectory: "Locales"),
              let data = try? Data(contentsOf: url),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return nil
        }
        return json
    }

    private func lookup(_ key: String, in table: [String: Any]) -> String? {
        let parts = key.split(separator: ".").map(String.init)
        var current: Any? = table
        for part in parts {
            guard let dict = current as? [String: Any] else { return nil }
            current = dict[part]
        }
        return current as? String
    }

    private func interpolate(_ template: String, params: [String: String]) -> String {
        params.reduce(template) { result, pair in
            result.replacingOccurrences(of: "{{\(pair.key)}}", with: pair.value)
        }
    }
}

@MainActor
func tr(_ key: String, params: [String: String] = [:]) -> String {
    I18n.shared.tr(key, params: params)
}

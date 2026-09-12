import Foundation

enum Formatters {
    static func money(_ amount: Double, currency: String?) -> String {
        let code = currency?.uppercased() ?? "GBP"
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = code
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: amount)) ?? String(format: "%.2f %@", amount, code)
    }

    static func shareLinkURL(token: String) -> String {
        "https://www.mybetrecord.com/share/\(token)"
    }

    static func publicProfileURL(token: String) -> String {
        "https://www.mybetrecord.com/u/\(token)"
    }
}

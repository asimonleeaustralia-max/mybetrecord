import Foundation
import Network

/// Observes path changes so the app can flush the sync outbox when connectivity returns.
@MainActor
final class NetworkMonitor: ObservableObject {
    @Published private(set) var isOnline = true

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "com.mybetrecord.network")
    private var onOnline: (() -> Void)?

    func start(onOnline: @escaping () -> Void) {
        self.onOnline = onOnline
        monitor.pathUpdateHandler = { [weak self] path in
            let online = path.status == .satisfied
            Task { @MainActor in
                guard let self else { return }
                let wasOffline = !self.isOnline
                self.isOnline = online
                if online, wasOffline {
                    self.onOnline?()
                }
            }
        }
        monitor.start(queue: queue)
    }

    func stop() {
        monitor.cancel()
    }
}

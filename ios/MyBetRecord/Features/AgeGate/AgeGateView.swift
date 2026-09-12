import SwiftUI

struct AgeGateView: View {
    let onConfirm: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Text("mybetrecord")
                .font(.largeTitle.bold())
                .foregroundStyle(.tint)
            Text("Age verification")
                .font(.title2.weight(.semibold))
            Text("You must be 18 or older to use this app. mybetrecord is a private betting ledger for tracking your own wagers — it does not accept bets or facilitate gambling.")
                .multilineTextAlignment(.center)
            Text("This app is for personal record-keeping only. If you have a gambling problem, seek help at begambleaware.org or your local support service.")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Spacer()
            Button("I am 18 or older", action: onConfirm)
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
            Link("Exit", destination: URL(string: "https://www.mybetrecord.com")!)
                .font(.footnote)
        }
        .padding(24)
    }
}

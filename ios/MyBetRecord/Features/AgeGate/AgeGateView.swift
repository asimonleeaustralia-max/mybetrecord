import SwiftUI

struct AgeGateView: View {
    let onConfirm: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Text("mybetrecord")
                .font(.largeTitle.bold())
                .foregroundStyle(.tint)
            Text(tr("ageGate.title"))
                .font(.title2.weight(.semibold))
            Text(tr("ageGate.message"))
                .multilineTextAlignment(.center)
            Text(tr("ageGate.disclaimer"))
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Spacer()
            Button(tr("ageGate.confirm"), action: onConfirm)
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
            Link(tr("ageGate.exit"), destination: URL(string: "https://www.mybetrecord.com")!)
                .font(.footnote)
        }
        .padding(24)
    }
}

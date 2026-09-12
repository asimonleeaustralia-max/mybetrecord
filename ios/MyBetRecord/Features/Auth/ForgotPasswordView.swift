import SwiftUI

enum ForgotPasswordStep {
    case request, confirm, done
}

struct ForgotPasswordView: View {
    @EnvironmentObject private var auth: AuthRepository
    @State private var step: ForgotPasswordStep = .request
    @State private var email = ""
    @State private var code = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var loading = false
    @State private var error: String?
    @State private var info: String?
    @State private var resendCooldown = 0
    let onBack: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(tr("auth.forgotPassword")).font(.title2)
                switch step {
                case .request:
                    requestStep
                case .confirm:
                    confirmStep
                case .done:
                    doneStep
                }
                if step != .done {
                    Button(tr("auth.backToSignIn"), action: onBack)
                }
            }
            .padding()
        }
        .onReceive(Timer.publish(every: 1, on: .main, in: .common).autoconnect()) { _ in
            if resendCooldown > 0 { resendCooldown -= 1 }
        }
    }

    @ViewBuilder
    private var requestStep: some View {
        Text(tr("auth.forgotPasswordHint")).foregroundStyle(.secondary)
        AppTextField(title: tr("auth.email"), text: $email, keyboard: .emailAddress)
        if let error { ErrorText(message: error) }
        Button(tr("auth.sendResetLink"), action: requestCode)
            .buttonStyle(.borderedProminent)
            .frame(maxWidth: .infinity)
            .disabled(loading)
    }

    @ViewBuilder
    private var confirmStep: some View {
        if let info { Text(info).foregroundStyle(.secondary) }
        AppTextField(title: tr("android.resetCode"), text: $code, keyboard: .numberPad)
        AppTextField(title: tr("auth.newPassword"), text: $newPassword, isSecure: true)
        AppTextField(title: tr("auth.confirmPassword"), text: $confirmPassword, isSecure: true)
        if let error { ErrorText(message: error) }
        Button(tr("auth.updatePassword"), action: confirmReset)
            .buttonStyle(.borderedProminent)
            .frame(maxWidth: .infinity)
            .disabled(loading)
        Button(resendCooldown > 0 ? tr("android.resendCodeIn", params: ["s": "\(resendCooldown)"]) : tr("android.resendCode"), action: requestCode)
            .disabled(loading || resendCooldown > 0)
        Button(tr("android.useDifferentEmail")) { step = .request }
    }

    @ViewBuilder
    private var doneStep: some View {
        Image(systemName: "checkmark.circle.fill")
            .font(.system(size: 48))
            .foregroundStyle(.tint)
        Text(tr("auth.passwordUpdated")).font(.headline)
        Text(tr("android.signInNewPassword")).foregroundStyle(.secondary)
        Button(tr("auth.backToSignIn"), action: onBack)
            .buttonStyle(.borderedProminent)
            .frame(maxWidth: .infinity)
    }

    private func requestCode() {
        loading = true
        error = nil
        Task {
            defer { loading = false }
            do {
                try await auth.requestPasswordReset(email: email)
                info = tr("auth.resetLinkSent")
                step = .confirm
                resendCooldown = 30
            } catch {
                self.error = error.userMessage
            }
        }
    }

    private func confirmReset() {
        guard newPassword == confirmPassword else {
            error = tr("auth.passwordMismatch")
            return
        }
        loading = true
        error = nil
        Task {
            defer { loading = false }
            do {
                try await auth.confirmPasswordReset(token: code, newPassword: newPassword)
                step = .done
            } catch {
                self.error = error.userMessage
            }
        }
    }
}

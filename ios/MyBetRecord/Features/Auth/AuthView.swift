import SwiftUI

struct AuthView: View {
    @EnvironmentObject private var auth: AuthRepository
    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var isRegister = false
    @State private var loading = false
    @State private var error: String?
    @State private var info: String?
    let onForgotPassword: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text("mybetrecord").font(.largeTitle.bold()).foregroundStyle(.tint)
                Text(isRegister ? tr("auth.createAccount") : tr("auth.signIn")).font(.title2)
                Text(tr("auth.tagline")).font(.footnote).foregroundStyle(.secondary)
                AppTextField(title: tr("auth.email"), text: $email, keyboard: .emailAddress)
                AppTextField(title: tr("auth.password"), text: $password, isSecure: true)
                if isRegister {
                    AppTextField(title: tr("auth.confirmPassword"), text: $confirmPassword, isSecure: true)
                } else {
                    Button(tr("auth.forgotPassword"), action: onForgotPassword)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
                if let error { ErrorText(message: error) }
                if let info { Text(info).foregroundStyle(.secondary) }
                Button(action: submit) {
                    Text(loading ? tr("meta.signingIn") : (isRegister ? tr("auth.createAccount") : tr("auth.signIn")))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(loading)
                Button(isRegister ? tr("auth.signIn") : tr("auth.createAccount")) {
                    isRegister.toggle()
                    error = nil
                    info = nil
                }
                .disabled(loading)
            }
            .padding()
        }
    }

    private func submit() {
        guard !email.isEmpty, !password.isEmpty else {
            error = "Email and password are required"
            return
        }
        if isRegister && password != confirmPassword {
            error = tr("auth.passwordMismatch")
            return
        }
        if isRegister && password.count < 8 {
            error = tr("auth.passwordInvalid")
            return
        }
        loading = true
        error = nil
        info = nil
        Task {
            defer { loading = false }
            do {
                if isRegister {
                    let message = try await auth.register(email: email, password: password, timezone: TimeZone.current.identifier)
                    info = message.isEmpty ? tr("auth.verificationLinkSent") : message
                    isRegister = false
                    password = ""
                    confirmPassword = ""
                } else {
                    try await auth.login(email: email, password: password)
                }
            } catch {
                self.error = error.userMessage
            }
        }
    }
}

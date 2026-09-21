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
                Text(isRegister ? trWithFallback("auth.createAccount", "Create Account") : trWithFallback("auth.signIn", "Sign In")).font(.title2)
                Text(trWithFallback("auth.tagline", "Personal betting ledger")).font(.footnote).foregroundStyle(.secondary)
                AppTextField(title: trWithFallback("auth.email", "Email"), text: $email, keyboard: .emailAddress)
                AppTextField(title: trWithFallback("auth.password", "Password"), text: $password, isSecure: true)
                if isRegister {
                    AppTextField(title: trWithFallback("auth.confirmPassword", "Confirm Password"), text: $confirmPassword, isSecure: true)
                } else {
                    Button(trWithFallback("auth.forgotPassword", "Forgot Password?"), action: onForgotPassword)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
                if let error { ErrorText(message: error) }
                if let info { Text(info).foregroundStyle(.secondary) }
                Button(action: submit) {
                    Text(loading ? trWithFallback("meta.signingIn", "Signing In...") : (isRegister ? trWithFallback("auth.createAccount", "Create Account") : trWithFallback("auth.signIn", "Sign In")))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(loading)
                Button(isRegister ? trWithFallback("auth.signIn", "Sign In") : trWithFallback("auth.createAccount", "Create Account")) {
                    isRegister.toggle()
                    error = nil
                    info = nil
                }
                .disabled(loading)
            }
            .padding()
        }
    }
    
    private func trWithFallback(_ key: String, _ fallback: String) -> String {
        let result = tr(key)
        return result == key ? fallback : result
    }

    private func submit() {
        guard !email.isEmpty, !password.isEmpty else {
            error = trWithFallback("auth.emailPasswordRequired", "Email and password are required")
            return
        }
        if isRegister && password != confirmPassword {
            error = trWithFallback("auth.passwordMismatch", "Passwords do not match")
            return
        }
        if isRegister && password.count < 8 {
            error = trWithFallback("auth.passwordInvalid", "Password must be at least 8 characters")
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
                    info = message.isEmpty ? trWithFallback("auth.verificationLinkSent", "Verification link sent to your email") : message
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

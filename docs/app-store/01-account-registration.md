# App Store — developer account enrollment

Owner runbook for enrolling in the Apple Developer Program for the mybetrecord iOS app.

## 1. Apple ID
- [ ] Create or choose a dedicated Apple ID (e.g. tied to `dev@mybetrecord.com`).
- [ ] Enable **two-factor authentication** (required).
- [ ] Store credentials in a password manager.

## 2. Enroll in the Apple Developer Program
1. Go to https://developer.apple.com/programs/enroll/
2. Sign in with your Apple ID.
3. Choose **Individual** (fastest for solo launch) or **Organization** (requires D-U-N-S number).
4. Pay the **US$99/year** fee.
5. Complete identity verification if prompted (can take 24–48 hours).

## 3. Accept agreements
- [ ] Sign in to [App Store Connect](https://appstoreconnect.apple.com).
- [ ] Accept any pending **License Agreement** updates under Agreements, Tax, and Banking.

## 4. Register the App ID
1. Open [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources).
2. **Identifiers → +** → App IDs → App → Continue.
3. Description: `mybetrecord`
4. Bundle ID (Explicit): `com.mybetrecord.ios` — **cannot change after first upload**.
5. Capabilities: none required beyond defaults (Keychain is automatic).

## 5. Xcode signing
- [ ] Open `ios/MyBetRecord.xcodeproj` in Xcode.
- [ ] Target **MyBetRecord → Signing & Capabilities**.
- [ ] Select your **Team** (the enrolled developer account).
- [ ] Ensure **Automatically manage signing** is enabled.

## Gate before proceeding
- Developer Program membership is active.
- App ID `com.mybetrecord.ios` exists.
- Xcode can sign the app for a physical device or simulator.

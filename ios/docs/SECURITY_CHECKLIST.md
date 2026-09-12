# Token & session handling
- [x] Access token held in memory only (`TokenStore`)
- [x] Refresh token in Keychain (`kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`)
- [x] Server rotates refresh tokens; reuse revokes the token family
- [x] Password reset / account deletion revoke all refresh tokens (server-side)
- [x] Logout calls `POST /auth/logout` and clears local session
- [x] API client refreshes on 401 and retries once

## Transport
- [x] Release: HTTPS-only (`https://www.mybetrecord.com`)
- [x] No IAP / Stripe / external payment links for digital subscriptions
- [x] Login sends `client: "ios"`

## Privacy & deletion
- [x] In-app account deletion with password + `DELETE` confirmation
- [x] Public web deletion URL: https://www.mybetrecord.com/delete-account
- [x] Privacy / terms / responsible-gambling links open in Safari
- [x] Privacy manifest (`PrivacyInfo.xcprivacy`) declares UserDefaults usage

## Pre-release checklist
- [ ] Unit tests pass (`xcodebuild test`)
- [ ] Manual smoke: login, CRUD bet, reports export, logout, delete account
- [ ] Age gate shown on first launch
- [ ] No upgrade CTAs; plan status read-only
- [ ] Archive signed with distribution certificate before App Store upload

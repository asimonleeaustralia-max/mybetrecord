# Android security & release checklist

Use this before every Play upload. Tick items after verification.

## Token & session handling
- [x] Access token held in memory only (`TokenStore`)
- [x] Refresh token in EncryptedSharedPreferences (Keystore AES-GCM)
- [x] Refresh token excluded from Auto Backup (`backup_rules.xml` / `data_extraction_rules.xml`)
- [x] Server rotates refresh tokens; reuse revokes the token family
- [x] Password change / reset / account deletion revoke all refresh tokens
- [x] Logout calls `POST /auth/logout` and clears local session
- [x] OkHttp authenticator refreshes on 401 and retries once

## Transport & permissions
- [x] Release: `usesCleartextTraffic=false` + HTTPS-only network security config
- [x] Debug: cleartext only for emulator localhost (`10.0.2.2`)
- [x] Manifest permissions limited to `INTERNET` (and optional `ACCESS_NETWORK_STATE` if added)
- [x] No bookmaker / upgrade / Stripe / Play Billing purchase paths in the app

## Logging & secrets
- [ ] OkHttp HTTP logging is `BODY` only in debug; `NONE` or headers-only in release
- [ ] No tokens, passwords, or full bet notes in logcat
- [ ] Upload keystore / signing secrets never committed to Git
- [ ] CI secrets stored in the secret manager only

## Privacy & deletion
- [x] In-app account deletion with password + `DELETE` confirmation
- [x] Public web deletion URL: https://www.mybetrecord.com/delete-account
- [x] Privacy / terms / responsible-gambling links open in browser
- [x] Data safety inventory matches runtime (`android/docs/DATA_SAFETY.md`)

## Threat review (manual)
- [ ] Stolen device: lock screen + EncryptedSharedPreferences verified
- [ ] Recent-apps / screenshots: `FLAG_SECURE` on auth screens if required
- [ ] Deep links: only intended App Links; no exported components with auth bypass
- [ ] Backup extraction: secure prefs excluded
- [ ] Dependency scan (`./gradlew dependencyCheckAnalyze` or OS/GitHub Dependabot)
- [ ] ProGuard/R8 mapping uploaded with each Play release

## Automated tests
- [ ] `./gradlew testDebugUnitTest` passes
- [ ] Backend `pytest tests/test_auth_mobile.py` passes
- [ ] Manual smoke: login, CRUD bet, reports, logout, delete account on a physical device
- [ ] Accessibility: TalkBack labels on primary actions; large font smoke
- [ ] Offline / poor network: error surfaces without crash

## Release engineering
- [ ] Version code bumped
- [ ] Signed AAB built with upload key (`./gradlew bundleRelease`)
- [ ] Play App Signing enrolled
- [ ] Reviewer demo account seeded with sample bets (no OTP/geo gate)
- [ ] Internal testing track validated before closed testing

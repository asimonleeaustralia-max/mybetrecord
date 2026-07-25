# Play Console — Data safety inventory

Inventory for the **mybetrecord** Android app (`com.mybetrecord.android`).  
Reconcile this document with the live build and privacy policy before every Play submission.

**Positioning:** Private historical betting ledger. Does not accept or facilitate wagers, process gambling funds, show odds feeds/tips, link to bookmakers for betting, serve gambling ads, or sell in-app subscriptions.

## Collection overview

| Data type (Play category) | Collected? | Shared? | Purpose | Encrypted in transit | User can request deletion |
|---------------------------|------------|---------|---------|----------------------|---------------------------|
| Email address | Yes (account) | No (processors only: hosting/email as needed to operate the service) | Account management, auth | Yes (HTTPS) | Yes |
| User IDs | Yes (server-assigned) | No | Account management | Yes | Yes |
| Other account info (display name, timezone, locale, odds format, bankroll preference, account description) | Yes (user-provided) | No | App functionality | Yes | Yes |
| Password | Collected at auth endpoints; stored server-side as hash only — **not** stored on device | No | Account management | Yes | N/A (credentials cleared on logout/deletion) |
| App activity — betting records (events, selections, stakes, odds, outcomes, notes, bookmaker labels entered by user) | Yes | No | App functionality | Yes | Yes |
| App info and performance / diagnostics (optional crash/ANR if Play vitals / future crash SDK) | Limited (OS / Play vitals by default; no third-party analytics SDK in v1) | Google Play (vitals) | Analytics / stability | Yes | N/A / via Play |
| Device or other IDs | Not collected by the app beyond standard TLS/network. Refresh token is a credential, not a device ID | No | Auth session | Yes | Yes (logout / delete account) |
| Approximate location / precise location | No | — | — | — | — |
| Contacts, photos, files, calendar, SMS | No | — | — | — | — |
| Financial info (payment card, purchase history) | **Not collected in the Android app.** Website subscriptions (if any) are out of band; app may show read-only plan status from `/auth/me` | No in-app payments | — | Yes for API | Account deletion |
| Health / sensitive personal | No | — | — | — | — |

## On-device storage

| Item | Storage | Backed up? |
|------|---------|------------|
| Access token | In-memory only | No |
| Refresh token | EncryptedSharedPreferences (Android Keystore-backed AES-GCM) | Excluded from backup / device transfer |
| Age attestation flag | DataStore preferences | Non-sensitive |
| Bets list cache | Room (SQLite) — ledger fields for offline-ish UX | Not auth material; cleared on account deletion / logout flows as applicable |

## Sharing / processors

- **No advertising SDKs, no Stripe SDK, no in-app billing SDK** in this app.
- Backend hosting and email delivery used by the web API may process account email and usage metadata under the privacy policy.
- Declare only processors that actually receive data from the Android client or backend for this product.

## Security practices (declare if accurate)

- Data encrypted in transit (HTTPS; cleartext disabled in release).
- Users can request deletion: in-app (`DELETE /auth/account`) and web (`https://www.mybetrecord.com/delete-account`).
- Independent security review recommended before production launch (see launch plan).

## Ephemeral / not collected

- Screenshots of auth screens may be blocked optionally via `FLAG_SECURE`.
- No microphone, camera, contacts, or location permissions in the manifest (Internet only).

## Reviewer notes (gambling positioning)

The app only records user-entered historical bets for personal analysis. It does not place wagers, hold gambling funds, provide tips/odds feeds, or include purchase/upgrade CTAs for digital subscriptions.

Update this inventory whenever SDKs, permissions, or collected fields change.

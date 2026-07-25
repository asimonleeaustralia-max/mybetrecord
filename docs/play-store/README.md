# mybetrecord — Play Store launch runbook

Step-by-step guide to ship the native Android app (`android/`) to Google Play under a personal developer account, with a consumption-only (no in-app purchase) model.

1. [Account registration & verification](01-account-registration.md)
2. [Signing & release build](02-signing-and-build.md)
3. [Store listing assets & declarations](03-listing-and-declarations.md)
4. [Closed testing, production access & rollout](04-closed-testing-and-launch.md)
5. [Reviewer / demo account](05-reviewer-access.md)

Related:
- App source & build: [`../../android/README.md`](../../android/README.md)
- Security checklist: [`../../android/docs/SECURITY_CHECKLIST.md`](../../android/docs/SECURITY_CHECKLIST.md)
- Data safety inventory: [`../../android/docs/DATA_SAFETY.md`](../../android/docs/DATA_SAFETY.md)
- API contract: [`../android-api-contract.md`](../android-api-contract.md)

## Key facts
- App/package: `mybetrecord` / `com.mybetrecord.android`
- Model: free, ad-free, **no in-app purchases** (Pro sold only on the website; app shows read-only plan status)
- Positioning: private historical betting ledger — does **not** accept/facilitate wagers, provide odds/tips, link bookmakers, hold funds, or show gambling ads
- Audience: adults (18+)
- Required legal URLs: `/privacy`, `/terms`, `/responsible-gambling`, `/delete-account` on `https://www.mybetrecord.com`
- New personal account => **12 testers / 14 days** closed test before production
- targetSdk 36 (Android 16) to satisfy the 31 Aug 2026 requirement

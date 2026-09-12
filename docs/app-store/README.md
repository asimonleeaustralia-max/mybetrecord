# mybetrecord — App Store launch runbook

Step-by-step guide to ship the native iOS app (`ios/`) to the Apple App Store under a new developer account, with a consumption-only (no in-app purchase) model.

1. [Account enrollment](01-account-registration.md)
2. [Signing, archive & upload](02-signing-and-build.md)
3. [Store listing, privacy & age rating](03-listing-and-declarations.md)
4. [TestFlight & production review](04-testflight-and-launch.md)
5. [Reviewer demo account](05-reviewer-access.md)

Related:
- App source & build: [`../../ios/README.md`](../../ios/README.md)
- Security checklist: [`../../ios/docs/SECURITY_CHECKLIST.md`](../../ios/docs/SECURITY_CHECKLIST.md)
- API contract: [`../mobile-api-contract.md`](../mobile-api-contract.md)

## Key facts
- Bundle ID: `com.mybetrecord.ios`
- Model: free, ad-free, **no in-app purchases** (Pro sold only on the website; app shows read-only plan status)
- Positioning: private historical betting ledger — does **not** accept/facilitate wagers, provide odds/tips, link bookmakers, hold funds, or show gambling ads
- Audience: adults (18+)
- Required legal URLs: `/privacy`, `/terms`, `/responsible-gambling`, `/delete-account` on `https://www.mybetrecord.com`
- Annual fee: **US$99** (Apple Developer Program)

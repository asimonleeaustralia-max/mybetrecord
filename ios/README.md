# mybetrecord iOS

Native Swift / SwiftUI client for [mybetrecord](https://www.mybetrecord.com).

- **Bundle ID:** `com.mybetrecord.ios`
- **Deployment target:** iOS 17+
- **Stack:** SwiftUI, SwiftData, URLSession, Keychain Services, Swift Charts

This app is a private betting ledger. It does **not** accept wagers, sell subscriptions, or include Stripe/checkout/upgrade CTAs.

## Prerequisites

- macOS with **Xcode 16+** (full Xcode, not Command Line Tools only)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)

## First-time setup

```bash
cd ios
xcodegen generate          # creates MyBetRecord.xcodeproj from project.yml
open MyBetRecord.xcodeproj
```

1. Select the **MyBetRecord** scheme and an iPhone simulator.
2. Set your **Development Team** in Signing & Capabilities (requires Apple Developer account).
3. Build and run (⌘R).

Release builds use `https://www.mybetrecord.com` as the API base URL (configured in `project.yml` / `Info.plist`).

## Build from the command line

```bash
cd ios
xcodegen generate
xcodebuild -scheme MyBetRecord \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  build
```

## Unit tests

```bash
xcodebuild -scheme MyBetRecord \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  test
```

Tests cover bet maths (Kelly, lay liability, fractional odds) and auth token persistence.

## Feature map

| Screen | Notes |
|--------|-------|
| Age gate | 18+ attestation on first launch |
| Auth | Login / register (`client: "ios"`) |
| Forgot password | Request code → confirm → done |
| Dashboard | Summary metrics, pull-to-refresh |
| Bets | CRUD, parlays, share links, SwiftData cache |
| Reports | Summary, equity curve, monthly chart, CSV/XLSX/JSON export |
| Tools | Kelly stake + lay liability calculators |
| Settings | Profile, locale (~100 languages), legal links, logout, account deletion |

## Localization

Locale JSON files live in `MyBetRecord/Resources/Locales/` (synced from the web app, plus mobile-specific keys).

They are bundled via XcodeGen as resource build-phase sources so `I18n` can load them at runtime. After editing `project.yml`, regenerate:

```bash
cd ios
xcodegen generate
```

Re-sync web locales (then re-merge any mobile-only keys if needed):

```bash
cp -R ../frontend/public/app/locales/* MyBetRecord/Resources/Locales/
```

Language can be changed in Settings; the UI refreshes immediately.

## App Store

See [`../docs/app-store/README.md`](../docs/app-store/README.md) for enrollment, signing, TestFlight, and review.

## Related docs

- API contract: [`../docs/mobile-api-contract.md`](../docs/mobile-api-contract.md)
- Security checklist: [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md)
- Privacy manifest: [`docs/PRIVACY_MANIFEST.md`](docs/PRIVACY_MANIFEST.md)

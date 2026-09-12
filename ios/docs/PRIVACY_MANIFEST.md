# Privacy manifest notes

The app includes `MyBetRecord/Resources/PrivacyInfo.xcprivacy` declaring:

- **No tracking** (`NSPrivacyTracking` = false)
- **Collected data:** email address and user-generated betting history, linked to identity, for app functionality only
- **Required reason API:** `UserDefaults` (CA92.1) for age attestation and locale preference

When completing **App Privacy** in App Store Connect, align labels with the above. The app does not use third-party analytics or advertising SDKs.

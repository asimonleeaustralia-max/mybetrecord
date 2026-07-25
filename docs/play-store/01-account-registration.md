# Play Console — personal account registration & verification

Owner runbook for registering the mybetrecord Android app under a **personal** Google Play developer account.

> Personal accounts created after 13 Nov 2023 must complete a 12-tester / 14-day closed test before production. See `04-closed-testing-and-launch.md`.

## 1. Owner Google account
- [ ] Create/choose a dedicated Google account to own the developer account (e.g. `dev@mybetrecord.com` or a personal Gmail).
- [ ] Enable 2-Step Verification (authenticator app) and set recovery email/phone.
- [ ] Store credentials in a password manager. Never share the owner login; add teammates as Play Console users with scoped permissions instead.

## 2. Register the developer account
1. Go to https://play.google.com/console/signup.
2. Choose account type: **Personal**.
3. Pay the one-time **US$25** registration fee (credit/debit card in your legal name).
4. Accept the Developer Distribution Agreement.

## 3. Identity verification
- [ ] Link a **personal Google Payments profile**. Legal name + address are taken from this profile.
- [ ] Ensure the legal name/address match your **government ID** and the **payment card**; mismatches forfeit the fee.
- [ ] Provide and verify (one-time password):
  - Contact email (Google → you)
  - Contact phone
  - Public developer email (shown on the store listing) — use `support@mybetrecord.com`
- [ ] Complete government-ID identity verification when prompted (may take a few days).

## 4. Device verification
- [ ] On the Play Console Home, open the "Verify that you have access to an Android mobile device" task.
- [ ] Install the **Play Console** mobile app on a **non-rooted physical Android 10+** device.
- [ ] Sign in as the account owner, select the developer account, tap **Verify**.

## 5. Create the app
- [ ] Play Console → **Create app**.
  - App name: `mybetrecord`
  - Default language: English (or your market's primary)
  - App or game: **App**
  - Free or paid: **Free**
- [ ] Set the package name at first upload: `com.mybetrecord.android` (permanent; cannot change later).
- [ ] Enroll in **Play App Signing** (required for new apps; let Google generate/manage the signing key, you keep the upload key).

## 6. Collaborators (optional, least privilege)
- [ ] Users and permissions → invite collaborators with only the roles they need (e.g. "Release manager" without financial/account access).

## Gate before proceeding
- Developer account is verified (identity + device).
- App entry exists with package `com.mybetrecord.android`.
- Play App Signing enabled.

# Play Console — account registration & verification

Owner runbook for registering the mybetrecord Android app on Google Play.

## 0. Choose the account type first (irreversible)

**The account type cannot be changed after registration.** Decide before paying.

| | Personal | Organisation |
|---|---|---|
| Requires | Government ID | ABN + **D-U-N-S number** + ID |
| Closed testing before production | **12 testers, opted in continuously for 14 days** | **Not required** |
| Fee | US$25 | US$25 |
| Lead time | Days (ID verification) | 1–4 weeks (D-U-N-S issuance) |

**Use Organisation.** mybetrecord operates commercially (Pro is sold on the
website) and an ABN is already held, so the Organisation route is available —
and it removes the closed-testing requirement entirely. The 12-tester rule is
the single biggest launch risk for a product without an existing user base:
the 14-day clock resets if the tester count drops below 12, and it depends on
a dozen other people staying opted in.

### Getting a D-U-N-S number
- [ ] **Check whether one already exists** — free lookup at dnb.com.au. Many
      ABN holders are already on file.
- [ ] If not, request one from Dun & Bradstreet. Free. Allow 1–4 weeks.
- [ ] **Make the details match exactly.** The legal business name and address
      on the D-U-N-S record must match the ABN record and what is entered in
      Play Console, character for character. Abbreviation mismatches
      ("St" vs "Street") and trading-name-vs-registered-name are the most
      common verification failures. Fix discrepancies with D&B *before*
      starting Play registration.

> If you register **Personal** instead, the 12-tester / 14-day closed test in
> `04-closed-testing-and-launch.md` becomes mandatory.

## 1. Owner Google account
- [ ] Create/choose a dedicated Google account to own the developer account (e.g. `dev@mybetrecord.com` or a personal Gmail).
- [ ] Enable 2-Step Verification (authenticator app) and set recovery email/phone.
- [ ] Store credentials in a password manager. Never share the owner login; add teammates as Play Console users with scoped permissions instead.

## 2. Register the developer account
1. Go to https://play.google.com/console/signup.
2. Choose account type: **Organisation** (see section 0 — this cannot be changed later).
3. Enter the D-U-N-S number and the matching legal business name/address.
4. Pay the one-time **US$25** registration fee.
5. Accept the Developer Distribution Agreement.

## 3. Identity & organisation verification
- [ ] Google verifies the organisation against the D-U-N-S record; expect a wait.
- [ ] Link the Google Payments profile. Legal name + address are taken from this profile and must match the D-U-N-S record.
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
- Account type is **Organisation** (or the closed-test requirement is accepted).
- Developer account is verified (organisation + identity + device).
- App entry exists with package `com.mybetrecord.android`.
- Play App Signing enabled.

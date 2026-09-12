# App Store — reviewer demo account

Apple App Review needs a working account to test the app. Prepare before submission.

## Requirements
- [ ] Dedicated email (e.g. `appreview+ios@mybetrecord.com` or similar)
- [ ] Email **verified** (complete registration verify flow if required)
- [ ] No 2FA / OTP gate that blocks automated review (use password-only login)
- [ ] Account pre-seeded with 3–5 sample bets (mixed outcomes, at least one multiple optional)
- [ ] Password stored in App Store Connect **App Review Information** only — never commit to Git

## App Review notes (paste into App Store Connect)

```
mybetrecord is a private betting LEDGER for tracking historical wagers the user has 
already placed elsewhere. The app does NOT:
- Accept or facilitate bets or wagers
- Display live odds or tips
- Link to bookmakers for placing bets
- Process payments or subscriptions (Pro is purchased on our website only)

Demo account:
Email: [REVIEWER_EMAIL]
Password: [REVIEWER_PASSWORD]

To test: sign in → view Dashboard → Bets → create/edit a bet → Reports → Settings → sign out.
Account deletion is available in Settings (requires password + typing DELETE).
Age gate: tap "I am 18 or older" on first launch.
```

## After rejection
- Read the Resolution Center message carefully.
- If asked about gambling: reiterate ledger-only positioning and point to website privacy/terms.
- If asked about payments: confirm no IAP; Pro is website-only with read-only status in app.

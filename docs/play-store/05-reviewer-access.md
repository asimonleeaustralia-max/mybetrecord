# Reviewer / demo account for Play review

The app is behind login, so Play review requires working credentials (App content → App access → Sign-in details).

## Requirements (per Play Console)
- Reusable, valid at all times, independent of location.
- No expiring password, OTP, or 2FA that a reviewer cannot bypass.
- Provided in English.

## Create the demo account
1. Register a normal account on production (`https://www.mybetrecord.com`) with a dedicated email, e.g. `playreview@mybetrecord.com`.
2. Verify the email so login works.
3. Seed representative data: ~15-20 sample bets across sports, some settled win/loss/void, a couple of multiples, so dashboard/reports render.
4. Confirm the account has a stable password that will not be rotated.

## Enter in Play Console
App content → **App access** → "All or some functionality is restricted" → add instructions:

```
Username: playreview@mybetrecord.com
Password: <stable password>

Steps:
1. Launch the app, accept the 18+ age confirmation.
2. Tap Sign in, enter the credentials above.
3. Dashboard, Bets, and Reports load from the account's sample data.
Notes: No OTP/2FA. Account works from any region. The app does not sell anything in-app.
```

## Maintenance
- Keep the account active and password unchanged; a broken login causes rejection.
- Re-seed data if it is ever cleared.

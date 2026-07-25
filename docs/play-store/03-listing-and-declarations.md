# Store listing assets & App content declarations

## Store listing text

**App name:** `mybetrecord`

**Short description (<=80 chars):**
> Private betting ledger: log bets, track P/L, and see your betting stats.

**Full description (draft):**
> mybetrecord is a private ledger for recording bets you have already placed and understanding your own results.
>
> - Log bets: event, selection, odds, stake, outcome, notes
> - Dashboard and reports: profit/loss, ROI, equity curve, breakdowns
> - Multiple odds formats and currencies
> - Sync with your mybetrecord.com account
>
> mybetrecord does not accept or facilitate wagers, provide tips or odds feeds, link you to bookmakers, or handle gambling funds. It is a personal record-keeping tool only — not betting or financial advice.
>
> Adults only (18+). Please gamble responsibly. Support: begambleaware.org, gamblingtherapy.org.

> Do not include price/promo text, ranking badges, or claims of guaranteed winnings. Do not imply Google endorsement.

## Graphic assets (required)
- [ ] App icon: 512x512 PNG (32-bit, <=1024 KB)
- [ ] Feature graphic: 1024x500 (JPEG or 24-bit PNG, no alpha)
- [ ] Phone screenshots: at least 4, 1080x1920 (portrait). Suggested: dashboard, bets list, add-bet, reports.
- [ ] Tablet screenshots: add after tablet QA (optional but recommended)

Asset rules: no bookmaker logos, no odds promotions, no winnings claims, no child-directed imagery.

## App content declarations (Policy and programs → App content)

| Declaration | Value for mybetrecord |
|-------------|-----------------------|
| Privacy policy URL | https://www.mybetrecord.com/privacy |
| Account deletion (external URL) | https://www.mybetrecord.com/delete-account |
| Ads | **No ads** |
| App access (sign-in) | Provide reviewer credentials (see `05-reviewer-access.md`) |
| Content rating (IARC questionnaire) | Complete honestly: simulated gambling references but **no real-money gambling**; expect a mature/adults rating |
| Target audience & content | **18+ only**; do not include children in target age groups |
| Data safety | Fill from `android/docs/DATA_SAFETY.md` |
| Financial features | Complete the declaration. The app itself offers no financial features (no loans, no crypto, no in-app payments). Declare accordingly |
| Government apps / News | No |

## Data safety form (summary — match runtime)
- Collects: email, user IDs, other account info, app activity (betting records the user enters).
- Purposes: account management, app functionality.
- Encrypted in transit: **Yes**.
- Data deletion: **Yes** — in-app and web URL.
- No advertising SDKs, no data sold, no location, no contacts.
- See full inventory: `android/docs/DATA_SAFETY.md`.

## Gambling positioning (critical)
mybetrecord is **not** a real-money gambling app under Play policy. In the content rating and any review notes, state clearly:

> The app only records historical bets that the user manually enters, for personal analysis. It does not enable wagering, does not process or hold gambling funds, has no odds/tips feed, contains no bookmaker links, and shows no gambling advertisements. There are no in-app purchases.

- Do **not** use Play In-app Billing for any digital subscription (there are none in the app).
- Do **not** include external upgrade/checkout links or CTAs (consumption-only; Pro is sold on the website out of band).
- If a reviewer classifies the build as facilitating gambling, **pause** and appeal with the above feature evidence rather than changing declarations.

## Distribution
- [ ] Start with the primary operating market (e.g. Australia) after checking local age/privacy/gambling-adjacent rules.
- [ ] Expand countries after policy/legal review.

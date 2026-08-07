# Launch sequencing & store visibility

Companion to the runbook in this folder. Docs 01–05 cover *how* to ship; this one covers *in what order*, *how long it really takes*, and *what can and cannot be done* about ranking once live.

Written 2 Aug 2026 against the state of the repo on that date.

## Verified build state

Checked directly, not assumed:

| Item | State |
|------|-------|
| `./gradlew bundleRelease` | Succeeds — 4.9 MB AAB |
| R8 / minification | Clean; kotlinx.serialization, Room and Hilt all survive shrinking |
| Release signing | Wired to a gitignored `android/keystore.properties` (see `02-signing-and-build.md`) |
| Unsigned fallback | With no `keystore.properties`, release builds still run and produce an **unsigned** artifact — Play rejects it loudly rather than accepting a debug-signed upload |
| targetSdk | 36 — already satisfies the 31 Aug 2026 requirement |

## Phase 1 — Blockers

Nothing else can start until these clear. Run them in parallel; the D-U-N-S is the long pole.

- [ ] **Start the D-U-N-S request first** (`01-account-registration.md`). It has
      the longest lead time and gates the Organisation account, which in turn
      is what removes the 12-tester closed-test requirement. Check whether one
      already exists before requesting.
- [ ] **Generate the upload keystore.** `keytool` command in `02-signing-and-build.md`. Create it outside the repo and back up the file *and* passwords to a password manager. Losing the upload key after first upload is recoverable through Play support; losing it before is not.
- [ ] **Create `android/keystore.properties`** with `storeFile`, `storePassword`, `keyAlias`, `keyPassword`. Absolute paths are safest; relative paths resolve against `android/`. The file is gitignored — keep it that way.
- [ ] **Register and verify the developer account** (`01-account-registration.md`). US$25, government-ID verification, device verification. Identity checks can take several days and gate everything downstream, so start this first.
- [ ] **Finish the offline write-path test.** Record a bet in airplane mode, confirm it queues and shows the pending banner, reconnect, confirm it syncs and gets a server id. The read path is verified on device; the write path has unit coverage but has not been exercised end to end. Closed testers will find it if you don't.

## Phase 2 — Store readiness

Can proceed while Phase 1 verification is pending.

- [ ] **Graphic assets** — the gap in `03-listing-and-declarations.md`. Icon 512×512, feature graphic 1024×500, 4+ phone screenshots at 1080×1920. The reports page (equity curve + metric cards) is the strongest screenshot available; bets list and the record-a-bet form fill the rest.
- [ ] **App content declarations** — the table in `03-listing-and-declarations.md` is already drafted and accurate. Work through it verbatim.
- [ ] **Data safety form** — fill from `../../android/docs/DATA_SAFETY.md`. Re-check it reflects runtime reality after the offline work: the app now stores a cached ledger, a write outbox and cached report data on device. All are local-only, cleared on sign-out and account deletion, and none of it leaves the device beyond the existing API calls — so the declared *collection* set is unchanged, but confirm the wording still fits.
- [ ] **Reviewer account** — `05-reviewer-access.md`.

## Phase 3 — Timeline

The dominant variable is the account type, decided at registration and
irreversible (`01-account-registration.md`).

**Organisation account (the chosen route):**

| Stage | Realistic duration |
|-------|--------------------|
| D-U-N-S issuance (if not already held) | 1–4 weeks |
| Account + organisation verification | 3–10 days |
| Internal testing, pre-launch report fixes | 2–4 days |
| Staged rollout 10 → 100% | 5–10 days |

**Roughly 3–6 weeks**, almost all of it waiting on D-U-N-S and verification —
so start that first and do the store assets while it processes.

**Personal account, for contrast:** adds a mandatory **12 testers opted in
continuously for 14 days** before you may even apply for production access,
plus a 3–7 day review of that application. Recruit 15–20 to absorb dropouts,
because the clock resets if the count falls below 12. For a product without an
existing user base this is the single biggest launch risk, which is why the
Organisation route is worth the paperwork.

## Visibility — what is actually achievable

No plan can guarantee a ranking. Play ranking is driven by install velocity, retention, ratings volume and recency, crash-free rate, and listing conversion rate. There is no lever that bypasses those, and anyone offering one is selling something.

Two constraints specific to this app, worth accepting up front:

**Editorial featuring is not a realistic target.** A new app in a gambling-adjacent category. Play's editorial team does not feature betting-related apps in the placements that drive meaningful volume. Do not build a plan around it.

**Paid acquisition is a risk, not a lever.** Google Ads restricts gambling-related advertising and requires certification in most countries. A record-keeping tool arguably is not gambling, but ad accounts get flagged on category signals and appeals are slow. Budget for the possibility that installs cannot be bought here at all.

### What does work, in order of expected return

1. **The website is the best channel, by a distance.** There are marketing pages, a blog, a sitemap and existing users with real betting history. An app-install prompt on `/app` and a note to existing web users reaches people with proven intent who already trust the product. This will outperform any keyword tactic.
2. **Own the long tail.** "bet tracker", "betting ledger", "punting record", "CLV tracker", "betting P/L". Low volume, high intent, winnable for a niche app. The **title field is the highest-weighted keyword surface** and currently spends all 30 characters on the brand name — something like `mybetrecord — Bet Tracker & P/L` uses it properly while staying clear of the promotional and ranking-claim language Play prohibits (see the asset rules in doc 03).
3. **Ratings volume feeds ranking, and there is currently no way to ask.** The app has no Play In-App Review integration. Adding it, prompted after a positive moment such as settling a winning bet, is a small change with a direct line to a real ranking input. Never gate features on leaving a review — that is a policy violation.
4. **Retention is already the structural advantage.** A ledger is inherently a returning-user product, and the offline work removes a whole class of "it didn't work on the train" churn. Retention weighs more heavily than any listing tweak.

### Do not

- Do not buy installs or reviews. Play detects it and it risks the account, not just the ranking.
- Do not put promo text, ranking badges, or winnings claims in listing assets — prohibited, and a policy strike here is far more expensive than the marginal click-through.
- Do not add in-app purchases to chase revenue signals. The consumption-only model is a deliberate policy position (doc 03); breaking it pulls the app into Play Billing obligations and re-opens the gambling-classification question.

## What to watch after launch

| Signal | Where | Act when |
|--------|-------|----------|
| Crash-free / ANR rate | Play vitals | Below Google's bad-behaviour threshold — ranking penalty and possible delisting |
| D1 / D7 retention | Play Console | Falling — the product problem outranks any ASO work |
| Listing conversion | Play Console → store performance | Low with healthy traffic means the screenshots or short description are the bottleneck, not keywords |
| Rating average and volume | Play Console | Sustained below ~4.0 — fix the cause before spending on acquisition |
| Auth / API error rates | Backend | Spikes during staged rollout — halt per doc 04 |

## Gate before applying for production

- [ ] All launch gates in `04-closed-testing-and-launch.md` are green.
- [ ] Signed AAB uploads cleanly and Play App Signing is enrolled.
- [ ] Offline write path verified end to end on a real device.
- [ ] Store listing contains no promotional, ranking or winnings language.
- [ ] Data safety declaration matches what the app actually stores on device.

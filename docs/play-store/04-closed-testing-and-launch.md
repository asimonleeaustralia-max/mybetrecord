# Closed testing, production access & staged rollout

Personal accounts (created after 13 Nov 2023) must pass a closed test before production.

## 0. Internal testing first
- [ ] Upload the signed AAB to **Internal testing**.
- [ ] Add yourself + a couple of devices; verify install, login, CRUD, reports, logout, delete account.
- [ ] Review the **Pre-launch report** (crashes, ANRs, accessibility, security). Fix criticals.

## 1. Closed test setup
- [ ] Testing → **Closed testing** → create a track (or use the default "Alpha").
- [ ] Add testers via email list or Google Group.
- [ ] Set countries to include wherever your testers live.
- [ ] Roll out the release to the closed track and wait for approval.

## 2. Meet the 12 / 14 requirement
- Requirement: **at least 12 testers opted in, continuously, for 14 days**.
- Recruit **15-20** genuine testers (real Android devices, real Google accounts) to absorb dropouts.
- The 14-day clock starts only after the release is approved **and** 12+ testers are opted in.
- Testers must click the opt-in link, install from Play, and stay opted in. If the count drops below 12, the clock can reset — monitor daily.
- [ ] Collect structured feedback; ship at least one improved build; document what changed.

## 3. Apply for production access
- [ ] Dashboard → **Apply for production access**.
- [ ] Answer honestly: how testers were recruited, engagement, feedback received, changes made.
- [ ] Wait for Google's review of the application.

## 4. Production release (staged rollout)
- [ ] Create a Production release with the reviewed AAB.
- [ ] Confirm all App content tasks are green (privacy, data safety, ratings, access, target audience, financial, ads).
- [ ] Staged rollout: **10% -> 25% -> 50% -> 100%**, monitoring at each step:
  - Play vitals (crash rate, ANR rate)
  - Backend auth/API error rates and refresh-token reuse events
  - Reviews / support inbox
- [ ] Halt/rollback if crash or auth error rates spike.

## 5. Post-launch ownership
- Monthly: dependency + Play policy review; rotate secrets/keys on schedule.
- Before **31 Aug 2026** and annually: keep targetSdk at the required API level (currently API 36).
- Update Data safety + privacy policy whenever collected data or SDKs change.
- Handle account-deletion requests and support promptly.
- Keep crash/ANR alerts and release notes; define rollback criteria.

## Launch gates (must all be true)
- [ ] Backend refresh/revocation + deletion flows deployed and tested.
- [ ] Legal pages live and accurate: `/privacy`, `/terms`, `/responsible-gambling`, `/delete-account`.
- [ ] No wager placement, bookmaker links/ads, odds/tips, gambling-fund handling, Stripe checkout, or upgrade CTA in the Android build.
- [ ] Security review, Data safety audit, reviewer access, internal QA, and 12-tester/14-day closed test complete.
- [ ] Play Console shows no unresolved policy tasks, pre-launch critical findings, or broken URLs.

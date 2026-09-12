# App Store — TestFlight & production launch

## 1. TestFlight internal testing
- [ ] After build processing completes, enable **Internal Testing**.
- [ ] Add yourself and up to 100 internal testers (App Store Connect users).
- [ ] Install via TestFlight app; smoke-test all flows against production API.

## 2. TestFlight external testing (optional)
- [ ] Create an external group; first build requires Beta App Review (usually faster than full review).
- [ ] Share public link or invite testers by email.

## 3. Pre-submission checklist
- [ ] Age gate works on fresh install
- [ ] Login / register / forgot password
- [ ] Bet CRUD + share link
- [ ] Reports + export share sheet
- [ ] Settings save + logout
- [ ] In-app account deletion
- [ ] No Stripe / upgrade / IAP UI
- [ ] Unit tests pass locally

## 4. Submit for review
1. App Store Connect → your app → **App Store** tab.
2. Create a new version (e.g. `1.0.0`).
3. Select the TestFlight build.
4. Complete **App Review Information**:
   - Contact info
   - Demo account (see `05-reviewer-access.md`)
   - Notes explaining the app is a **ledger/tracker**, not a sportsbook
5. **Submit for Review**.

## 5. Review timeline
- Typical: 24–48 hours; first submission may take longer.
- If rejected, address the specific guideline cited (common: 4.7 gambling, 3.1.1 payments, 5.1.1 account deletion).

## 6. Release
- [ ] Choose **Manually release** or **Automatic** after approval.
- [ ] Monitor crash reports in Xcode Organizer / App Store Connect.

## 7. Post-launch
- [ ] Bump build number for each subsequent upload.
- [ ] Keep demo reviewer account seeded with sample bets.

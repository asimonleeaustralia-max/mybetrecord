# App Store — listing, privacy & age rating

## 1. Create the app record
- [ ] App Store Connect → **My Apps** → **+** → New App.
- [ ] Platform: iOS
- [ ] Name: `mybetrecord`
- [ ] Primary language: English
- [ ] Bundle ID: `com.mybetrecord.ios`
- [ ] SKU: `mybetrecord-ios` (internal identifier)

## 2. Store listing
- [ ] **Subtitle** (optional): e.g. "Your private betting ledger"
- [ ] **Description**: emphasize personal record-keeping, no wagering, no IAP, free and ad-free.
- [ ] **Keywords**: betting tracker, ledger, journal, sports betting record (avoid "sportsbook", "wager")
- [ ] **Support URL**: https://www.mybetrecord.com
- [ ] **Marketing URL** (optional): https://www.mybetrecord.com
- [ ] **Privacy Policy URL**: https://www.mybetrecord.com/privacy

## 3. Screenshots
Required for iPhone (6.7" display minimum). Capture:
- Dashboard / summary
- Bets list
- Bet editor
- Reports with chart
- Settings (showing legal links)

## 4. App icon
- [ ] 1024×1024 PNG (no transparency, no rounded corners — Apple applies mask).

## 5. Age rating
Complete the questionnaire honestly. Expect **17+** due to gambling-adjacent content, even though the app does not facilitate wagering.

## 6. App Privacy (Nutrition Labels)
Declare per `ios/docs/PRIVACY_MANIFEST.md`:
- Email address — linked to user, app functionality
- User content (betting history) — linked to user, app functionality
- **No** tracking across apps/websites
- **No** data used for advertising

## 7. Category
- Primary: **Finance** or **Sports** (ledger positioning — avoid Gambling category)
- Secondary (optional): Sports

## 8. Pricing
- [ ] Free (no in-app purchases)

## 9. Content rights & export compliance
- [ ] Standard encryption (HTTPS only) — typically qualifies for exemption; answer App Store Connect export questions accordingly.

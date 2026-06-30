# Mobile browser testing

Manual checklist for validating MyBetRecord on real devices and browsers. Automated coverage lives in `e2e/` (Playwright) and Lighthouse CI.

## Supported browsers

| Platform | Minimum version |
|----------|-----------------|
| iOS Safari | 12+ |
| Chrome Android | 80+ |
| Samsung Internet | 12+ |
| Desktop Safari, Chrome, Firefox | Last 2 major versions |

Not supported: Internet Explorer 11, pre-Chromium Edge.

## Real-device checklist

### iOS (Safari)

- [ ] **iPhone SE (1st gen) or iPhone 8** — Safari 12–15: auth login, record bet, scroll ledger table
- [ ] **Current iPhone** — Safari: full auth → bet → reports flow; charts or table fallback visible
- [ ] **Private browsing** — sign in works; ephemeral-storage toast appears; session lost after closing tab
- [ ] **Add to Home Screen** — app shell loads at `/app/`; sticky header stays visible while scrolling
- [ ] **Landscape** — bet form fields remain usable; no clipped submit button
- [ ] **datetime-local** — date pickers open for event/placed/settled fields
- [ ] **Notched device** — toast and modal clear home indicator (safe-area insets)

### Android

- [ ] **Chrome** — auth, bet entry, reports, settings
- [ ] **Samsung Internet** — landing page header layout at 360px and 412px width
- [ ] **Low-memory device** — reports page loads (Chart.js or numeric table fallback)
- [ ] **Slow 3G** — landing and `/app/` become interactive without long blank screen

### Cross-cutting

- [ ] Ledger table scrolls horizontally inside `.table-wrap` without breaking page layout
- [ ] Row action buttons (edit/delete/share) are easy to tap (44px touch targets on coarse pointers)
- [ ] Delete bet / revoke share / cancel plan use in-app modal (not native `confirm()`)
- [ ] Copy share link works (clipboard or fallback)
- [ ] Stripe checkout redirect on staging (Pro upgrade)
- [ ] Locale selector on marketing pages; `/app/` respects user locale

## Automated tests (CI)

```bash
# Build frontend
cd frontend && npm ci && npm run build

# Start full stack
docker compose up -d --build --wait

# Playwright (Pixel 5, iPhone 12, iPhone SE, Desktop Safari)
cd e2e && npm ci && npx playwright install --with-deps chromium webkit && npm test

# Lighthouse mobile audits
cd e2e && npx lhci autorun --config=../.lighthouserc.js

docker compose down -v
```

## Frontend development

Source JavaScript lives in `frontend/src/`. After editing, rebuild:

```bash
cd frontend && npm run build
```

Built assets are written to `frontend/public/app/` and `frontend/public/marketing.js`.

# mybetrecord

A betting ledger for people who bet to a number. Record every bet with the
context that matters — odds in any format, your model's price, your own price,
Kelly stake, closing line, winnings deductions — then see ROI, yield, strike
rate, an equity curve, and breakdowns by sport, tipster, or bet type. Export
to CSV or Excel, and drive the whole thing from an API if you want to.

Python (FastAPI) microservices, PostgreSQL, a vanilla-JS mobile-responsive
frontend, deployed to Azure Container Apps with Bicep.

---

## Architecture

```
                         ┌─────────────────────────────┐
   browser / mobile ───▶ │  frontend (nginx + SPA)      │  external ingress
                         │  reverse-proxies by path     │
                         └───┬─────┬─────────┬──────────┘
                  /auth/ ────┘     │ /reports/         └──── /payments/
                                   │ /bets
              ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
              │  auth    │  │  bets    │  │ reports  │  │ payments │   internal
              │  :8001   │  │  :8002   │  │  :8003   │  │  :8004   │   ingress
              └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
                   └─────────────┴──────┬──────┴─────────────┘
                                  ┌─────────────┐
                                  │ PostgreSQL  │
                                  └─────────────┘
```

| Service | Owns | Key endpoints |
|---|---|---|
| **auth** | users, login, settings, API keys, password reset | `/auth/register`, `/auth/login`, `/auth/me`, `/auth/settings`, `/auth/api-keys`, `/auth/password-reset/request`, `/auth/password-reset/confirm` |
| **bets** | bet CRUD, odds normalisation, P/L + Kelly on write, sports list | `/bets`, `/bets/{id}`, `/bets/sports` |
| **reports** | analytics, exports | `/reports/summary`, `/reports/equity-curve`, `/reports/breakdown`, `/reports/export.csv`, `/reports/export.xlsx` |
| **payments** | Stripe Pro subscriptions (off without keys) | `/payments/checkout-session`, `/payments/webhook`, `/payments/promo`, `/payments/portal-session` |
| **frontend** | SPA + same-origin reverse proxy | — |

The domain logic — odds conversion, implied probability, Kelly, settlement,
and portfolio metrics — lives in one place: `shared/betrecord_shared/betting_math.py`.
Every service imports it, so "what is the P/L of this bet" has exactly one answer.

---

## What gets recorded

Event, selection, sport, bet type (win / each-way / over-under / multi /
handicap), odds (decimal, American, or fractional — stored canonically as
decimal), date & time, stake and currency, result (win / loss / void /
half-win / half-loss / pending), P/L (net of any winnings deduction %), cash-out
amount, bet model, model implied odds, personal implied odds, Kelly stake
recommendation, closing odds, bookmaker, winnings deduction % (e.g. exchange
commission), tipster,
and free-text notes. Previously used sports are offered as an autocomplete
dropdown on the entry form.

**Derived automatically:** decimal odds from any input format, net P/L
(including each-way settlement, half-win/half-loss, cash-out override, and
winnings deductions on winners), Kelly stake (from your bankroll and personal
implied odds), closing-line value, and per-unit edge.

---

## Run it locally

Requires Docker.

```bash
docker compose up --build
# open http://localhost:8080
```

That starts Postgres, all four services, and the frontend. Create an account, set your **default entry odds** format and bankroll under
**Settings** (bankroll is used for the Kelly recommendation), and record a bet.

### Plans & billing

- **Free** — up to 5 single bets and 5 multiple/parlay bets per day (configurable via `FREE_DAILY_BET_LIMIT` / `FREE_DAILY_MULTIPLE_LIMIT`).
- **Pro** — unlimited daily bets, ~$5 USD/month (20 currencies; see `shared/betrecord_shared/pricing.py`).

Billing is **optional**. Without `STRIPE_SECRET_KEY`, everyone stays on Free and upgrade buttons show as unavailable.

To enable billing locally, set in `.env` or `docker-compose` overrides:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...   # from Stripe CLI or Dashboard webhook
STRIPE_PRODUCT_ID=prod_...          # optional — groups prices in Stripe Dashboard
```

Forward webhooks during local dev:

```bash
stripe listen --forward-to localhost:8080/payments/webhook
```

**Stripe Dashboard setup (test + live):**

1. Create a Product (e.g. `mybetrecord Pro`) — optional `STRIPE_PRODUCT_ID`.
2. Register webhook `https://<your-domain>/payments/webhook` with events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`.
3. Configure [Customer Portal](https://dashboard.stripe.com/settings/billing/portal) for payment-method updates and invoices.
4. **Promotion codes** — create a Coupon (e.g. 20% off for 3 months), then a Promotion Code (e.g. `LAUNCH20`). Share via email or deep link `/app?promo=LAUNCH20#/settings`. Codes can also be entered on Stripe Checkout or in Settings before upgrade.

Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

Past-due subscriptions still grant Pro access (`past_due` is treated as active) until Stripe cancels the subscription.

### Password reset

Users can reset their password from the sign-in screen (**Forgot password?**). The
auth service emails a single-use link valid for 60 minutes (configurable via
`PASSWORD_RESET_MINUTES`). Links are built as `{FRONTEND_URL}/app/#/reset-password/{token}`.

**Local development:** without SMTP configured, reset emails are printed to the
auth service container logs (`docker compose logs auth`). In non-production mode
the API also returns a `reset_token` field for testing.

**Production:** set `FRONTEND_URL` to your public site origin (e.g.
`https://www.mybetrecord.com`) and configure SMTP on the auth service. Any SMTP
provider works — SendGrid (`smtp.sendgrid.net`), Mailgun, etc. See
`.env.deploy.example` for the full variable list.

```bash
# Request a reset link
curl -X POST https://<your-site>/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'

# Confirm with the token from the email
curl -X POST https://<your-site>/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"token":"<token-from-email>","password":"new-password123"}'
```

### Inbound email (support@)

The site links to `support@mybetrecord.com`, `privacy@mybetrecord.com`, and
`legal@mybetrecord.com`. Inbound mail is separate from outbound SMTP (verification
and password-reset emails). Use a forwarding service such as
[ImprovMX](https://improvmx.com) if your DNS is not on Cloudflare.

1. Create an ImprovMX account and add `mybetrecord.com`.
2. In ImprovMX, open **Domain Settings** (cogwheel) → **DNS Settings** — copy the
   MX and SPF values shown there (there is no separate `improvmx-verification`
   string; ImprovMX verifies your domain once MX + SPF records are live in DNS).
3. **Add MX and SPF records in GoDaddy** (see below).
4. Create forwarding aliases to your personal inbox:
   - `support@mybetrecord.com` (required)
   - `privacy@mybetrecord.com` and `legal@mybetrecord.com` (recommended — linked from the site)
5. Confirm the destination address via ImprovMX’s verification email.
6. In ImprovMX, click **Check Again** until the domain shows **Email forwarding
   active**, then send a test message to `support@mybetrecord.com`.

#### GoDaddy: MX and SPF records (steps 2–3)

ImprovMX does **not** give you a one-off verification code. You add these fixed
records in GoDaddy; ImprovMX detects them automatically.

1. Sign in at [godaddy.com](https://www.godaddy.com) → **My Products**.
2. Next to **mybetrecord.com**, click **DNS** (or **Manage DNS**).
3. Remove any existing **MX** records for `@` (old GoDaddy email, Microsoft
   365, etc.) — only one inbound mail provider can own MX for a domain.
4. Add two **MX** records:

   | Type | Name | Value | Priority | TTL |
   |------|------|-------|----------|-----|
   | MX | `@` | `mx1.improvmx.com` | 10 | 1 Hour |
   | MX | `@` | `mx2.improvmx.com` | 20 | 1 Hour |

5. Add one **TXT** record for SPF (this is not a verification code — it tells
   other mail servers ImprovMX may handle mail for your domain):

   | Type | Name | Value | TTL |
   |------|------|-------|-----|
   | TXT | `@` | `v=spf1 include:spf.improvmx.com ~all` | 1 Hour |

   If you already have an SPF TXT record on `@`, **merge** ImprovMX into it
   (do not create a second SPF record). See
   [ImprovMX: combining SPF records](https://improvmx.com/guides/combining-spf-records).

6. Click **Save** on each record.
7. Back in ImprovMX → **Domain Settings** → **DNS Settings**, click **Check
   Again**. Status changes to **Email forwarding active** once DNS has propagated
   (usually 5–30 minutes; can take up to 24 hours).

**Notes:**

- Do **not** change your existing **A**, **CNAME**, or **ALIAS** records for
  `www` / `@` — those keep the website on Azure.
- If **nameservers** on the GoDaddy DNS page point elsewhere, add MX/SPF at that
  DNS host instead.
- Verify records with [ImprovMX Inspector](https://inspector.improvmx.com/).

MX records only affect inbound delivery; they do not change your web hosting
(CNAME/A for `www` / apex) or outbound SMTP.

If DNS is on Cloudflare, you can use [Cloudflare Email Routing](https://developers.cloudflare.com/email-routing/) instead (free forwarding).

### Without Docker

`scripts/run_local.py` runs the whole app on SQLite with a built-in static +
reverse-proxy server standing in for nginx — no database or Docker to install:

```bash
pip install ./shared
pip install -r services/auth/requirements.txt -r services/bets/requirements.txt \
            -r services/reports/requirements.txt -r services/payments/requirements.txt
python scripts/run_local.py        # -> http://localhost:8080
```

To run a single service against your own Postgres instead:

```bash
DATABASE_URL=postgresql+psycopg://betrecord:betrecord@localhost:5432/betrecord \
  uvicorn app.main:app --app-dir services/bets --port 8002
```

Run the tests:

```bash
pip install ./shared pytest
pytest -q
```

---

## Deploy to Azure

Deployment is Bicep (`infra/main.bicep`) → a Container Apps environment, an
Azure Container Registry, a PostgreSQL Flexible Server, Log Analytics, and the
five container apps.

### Deploy from Cursor (or your terminal)

One script drives the full flow (tests → ACR build → Bicep). In Cursor, ask
the agent to **deploy to Azure** — it will run `scripts/deploy.sh` using the
rule in `.cursor/rules/azure-deploy.mdc`.

```bash
cp .env.deploy.example .env.deploy   # once
# Edit .env.deploy: PG_ADMIN_PASSWORD, JWT_SECRET, FRONTEND_URL, SMTP_*, optional CORS / Stripe

az login
./scripts/deploy.sh                  # first time auto-bootstraps if no ACR yet
./scripts/deploy.sh --skip-tests     # hotfix when tests already passed
./scripts/deploy.sh --dry-run        # preview steps
```

The deployment output `frontendUrl` is your live site.

### Manual deploy (step by step)

```bash
# 1. Resource group
az group create -n mybetrecord-rg -l australiaeast

# 2. Infra + a registry to push to
az deployment group create -g mybetrecord-rg -n main \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --parameters pgAdminPassword='<strong-password>' jwtSecret='<long-random>'

# 3. Build & push images to the created ACR (name is in the deployment output)
ACR=$(az acr list -g mybetrecord-rg --query "[0].name" -o tsv)
for s in auth bets reports payments; do
  az acr build --registry $ACR --image $s:latest --file services/$s/Dockerfile .
done
az acr build --registry $ACR --image frontend:latest --file frontend/Dockerfile .

# 4. Re-run step 2 so the apps pick up the freshly pushed images.
```

**Point mybetrecord.com at it:** add the domain to the frontend container app
(`az containerapp hostname add` + a managed certificate), then create the DNS
records Azure shows you at your registrar. Set `corsOrigins` to that URL.

### CI/CD

`.github/workflows/ci-cd.yml` runs the tests on every push/PR, then on `main`
calls `./scripts/deploy.sh --skip-tests` after Azure OIDC login. Configure these
repo secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
`PG_ADMIN_PASSWORD`, `JWT_SECRET`, and (optionally) `FRONTEND_URL`, `SMTP_HOST`,
`SMTP_USER`, `SMTP_PASSWORD`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
`STRIPE_PRODUCT_ID`.

### Why Container Apps instead of bare Container Instances

You asked for "microservices in Azure Container Instances." The same images run
on ACI, but ACI gives you no built-in internal service discovery, ingress, or
per-service autoscaling — you'd hand-roll all of it. Container Apps provides
internal DNS between services, managed HTTPS ingress, and scale rules out of the
box, which is what a microservices web app actually needs. If you specifically
want ACI, deploy each image with `az container create` into a VNet and put the
frontend's proxy targets at the other containers' private IPs.

---

## Using the API

Generate a key under **Settings → API access**. Send it as a bearer token (the
same endpoints accept either a login JWT or an API key):

```bash
KEY="mbr_xxxxxxxx..."

# Record a bet
curl -X POST https://<your-site>/bets \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"event":"14:30 Ascot","selection":"Galileo Gold","sport":"Horse racing",
       "bet_type":"win","odds":2.5,"odds_format":"decimal","stake":100,
       "outcome":"win","personal_implied_odds":2.1,"closing_odds":2.3,
       "bookmaker":"Betfair","exchange_commission_pct":5}'

# Pull your summary, or export
curl https://<your-site>/reports/summary -H "Authorization: Bearer $KEY"
curl https://<your-site>/reports/export.csv -H "Authorization: Bearer $KEY" -o record.csv
```

Each service serves interactive OpenAPI docs at `/docs`.

---

## Production hardening checklist

- Move Postgres behind VNet integration + a private endpoint; drop the
  `AllowAllAzureServices` firewall rule.
- Switch ACR auth from admin user to a managed identity on the container apps.
- Put `JWT_SECRET`, the DB password, and Stripe keys in Azure Key Vault and
  reference them as secrets.
- Replace `init_db()` (dev-only `create_all`) with Alembic migrations.
- Set `corsOrigins` to your real domain only.

## Layout

```
shared/betrecord_shared/   domain models, schemas, security, betting math
services/{auth,bets,reports,payments}/   one FastAPI app each
frontend/                  nginx + the SPA (index.html, styles.css, app.js)
infra/main.bicep           Azure deployment
scripts/deploy.sh          deploy to Azure (Cursor / CI / terminal)
tests/                     betting-math unit tests
docker-compose.yml         local dev
```

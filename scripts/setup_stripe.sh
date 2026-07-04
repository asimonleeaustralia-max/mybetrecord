#!/usr/bin/env bash
# Wire Stripe billing for mybetrecord (Pro subscriptions via Checkout Sessions).
#
# The app code is already integrated — this script connects your Stripe account:
#   1. Ensures a "mybetrecord Pro" Product exists (optional but recommended)
#   2. Writes STRIPE_* vars into .env (local) and/or .env.deploy (Azure)
#   3. Prints webhook + Customer Portal setup steps
#
# Usage (from repo root):
#   STRIPE_SECRET_KEY=sk_test_... ./scripts/setup_stripe.sh
#   STRIPE_SECRET_KEY=sk_test_... ./scripts/setup_stripe.sh --local
#   STRIPE_SECRET_KEY=sk_live_... ./scripts/setup_stripe.sh --production --deploy
#
# Requires: curl, jq (optional but recommended)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PRODUCT_NAME="mybetrecord Pro"
PRODUCT_DESCRIPTION="Unlimited bets, full analytics, CSV/Excel export, and API access."
WEBHOOK_EVENTS=(
  checkout.session.completed
  customer.subscription.created
  customer.subscription.updated
  customer.subscription.deleted
)
LOCAL_WEBHOOK_URL="http://localhost:8080/payments/webhook"
PRODUCTION_WEBHOOK_URL="${PRODUCTION_WEBHOOK_URL:-https://www.mybetrecord.com/payments/webhook}"

MODE="both"   # local | production | both
RUN_DEPLOY=0
ENV_FILE=""
DEPLOY_FILE=""

usage() {
  cat <<'EOF'
Connect Stripe billing to mybetrecord.

Options:
  --local         Update .env for docker compose / local dev only
  --production    Update .env.deploy for Azure deploy only
  --deploy        After updating .env.deploy, run ./scripts/deploy.sh --skip-tests
  -h, --help      Show this help

Environment:
  STRIPE_SECRET_KEY      Required (sk_test_... or sk_live_...)
  STRIPE_WEBHOOK_SECRET  Optional — set after creating a webhook endpoint
  STRIPE_PRODUCT_ID      Optional — skip product creation when already known
  PRODUCTION_WEBHOOK_URL Override production webhook URL (default: https://www.mybetrecord.com/payments/webhook)

Examples:
  STRIPE_SECRET_KEY=sk_test_xxx ./scripts/setup_stripe.sh --local
  stripe listen --forward-to localhost:8080/payments/webhook   # separate terminal for local webhooks
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) MODE="local"; shift ;;
    --production) MODE="production"; shift ;;
    --deploy) RUN_DEPLOY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

load_secret_key() {
  if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
    return 0
  fi
  local files=("$ROOT/.env" "$ROOT/.env.deploy")
  if [[ "$MODE" == "production" ]]; then
    files=("$ROOT/.env.deploy" "$ROOT/.env")
  elif [[ "$MODE" == "local" ]]; then
    files=("$ROOT/.env" "$ROOT/.env.deploy")
  fi
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      local val
      val="$(grep -E '^STRIPE_SECRET_KEY=' "$f" | head -1 | cut -d= -f2- || true)"
      if [[ -n "$val" ]]; then
        STRIPE_SECRET_KEY="$val"
        return 0
      fi
    fi
  done
  echo "Set STRIPE_SECRET_KEY (sk_test_... / rk_live_... etc.) in the environment or .env.deploy." >&2
  echo "Dashboard: https://dashboard.stripe.com/apikeys" >&2
  exit 1
}

stripe_api() {
  local method="$1"
  local path="$2"
  shift 2
  curl -sS -X "$method" "https://api.stripe.com/v1${path}" \
    -u "${STRIPE_SECRET_KEY}:" \
    "$@"
}

ensure_product() {
  if [[ -n "${STRIPE_PRODUCT_ID:-}" ]]; then
    echo "Using existing STRIPE_PRODUCT_ID=${STRIPE_PRODUCT_ID}"
    return 0
  fi

  echo "Looking for Stripe product \"${PRODUCT_NAME}\"..."
  local list_json
  list_json="$(stripe_api GET /products -G --data-urlencode "active=true" --data-urlencode "limit=100")"

  if command -v jq >/dev/null 2>&1; then
    if [[ "$STRIPE_SECRET_KEY" == sk_live_* || "$STRIPE_SECRET_KEY" == rk_live_* ]]; then
      STRIPE_PRODUCT_ID="$(echo "$list_json" | jq -r --arg n "$PRODUCT_NAME" \
        '.data[] | select(.name == $n and .livemode == true) | .id' | head -1)"
    elif [[ "$STRIPE_SECRET_KEY" == sk_test_* || "$STRIPE_SECRET_KEY" == rk_test_* ]]; then
      STRIPE_PRODUCT_ID="$(echo "$list_json" | jq -r --arg n "$PRODUCT_NAME" \
        '.data[] | select(.name == $n and .livemode == false) | .id' | head -1)"
    else
      STRIPE_PRODUCT_ID="$(echo "$list_json" | jq -r --arg n "$PRODUCT_NAME" \
        '.data[] | select(.name == $n) | .id' | head -1)"
    fi
  else
    STRIPE_PRODUCT_ID="$(echo "$list_json" | grep -o '"id": "prod_[^"]*"' | head -1 | cut -d'"' -f4 || true)"
  fi

  if [[ -n "$STRIPE_PRODUCT_ID" && "$STRIPE_PRODUCT_ID" != "null" ]]; then
    echo "Found product: ${STRIPE_PRODUCT_ID}"
    return 0
  fi

  echo "Creating product \"${PRODUCT_NAME}\"..."
  local create_json
  create_json="$(stripe_api POST /products \
    -d "name=${PRODUCT_NAME}" \
    -d "description=${PRODUCT_DESCRIPTION}" \
    -d "metadata[app]=mybetrecord" \
    -d "metadata[plan]=pro")"

  if command -v jq >/dev/null 2>&1; then
    STRIPE_PRODUCT_ID="$(echo "$create_json" | jq -r '.id // empty')"
    if echo "$create_json" | jq -e '.error' >/dev/null 2>&1; then
      echo "$create_json" | jq -r '.error.message' >&2
      exit 1
    fi
  else
    STRIPE_PRODUCT_ID="$(echo "$create_json" | grep -o '"id": "prod_[^"]*"' | head -1 | cut -d'"' -f4)"
  fi

  if [[ -z "$STRIPE_PRODUCT_ID" ]]; then
    echo "Failed to create product. Response:" >&2
    echo "$create_json" >&2
    exit 1
  fi
  echo "Created product: ${STRIPE_PRODUCT_ID}"
}

upsert_env() {
  local file="$1" key="$2" value="$3"
  if [[ ! -f "$file" ]]; then
    cp "${file%.deploy}" "$file" 2>/dev/null || cp "$ROOT/.env.example" "$file" 2>/dev/null || touch "$file"
  fi
  if grep -q "^${key}=" "$file"; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

update_env_files() {
  local target="$1"
  local file=""
  case "$target" in
    local) file="$ENV_FILE" ;;
    production) file="$DEPLOY_FILE" ;;
  esac

  upsert_env "$file" STRIPE_SECRET_KEY "$STRIPE_SECRET_KEY"
  if [[ -n "${STRIPE_PRODUCT_ID:-}" ]]; then
    upsert_env "$file" STRIPE_PRODUCT_ID "$STRIPE_PRODUCT_ID"
  else
    # Clear a stale product id (e.g. test-mode prod_ on a live key).
    if grep -q "^STRIPE_PRODUCT_ID=" "$file"; then
      sed -i '' 's|^STRIPE_PRODUCT_ID=.*|STRIPE_PRODUCT_ID=|' "$file"
    fi
  fi
  if [[ -n "${STRIPE_WEBHOOK_SECRET:-}" ]]; then
    upsert_env "$file" STRIPE_WEBHOOK_SECRET "$STRIPE_WEBHOOK_SECRET"
  fi
  echo "Updated ${file}"
}

print_webhook_instructions() {
  local label="$1" url="$2"
  echo ""
  echo "=== Webhook setup (${label}) ==="
  echo "Endpoint URL: ${url}"
  echo "Events to enable:"
  for ev in "${WEBHOOK_EVENTS[@]}"; do
    echo "  - ${ev}"
  done
  echo ""
  echo "Dashboard: https://dashboard.stripe.com/webhooks"
  echo "After creating the endpoint, copy the signing secret (whsec_...) into STRIPE_WEBHOOK_SECRET."
}

print_portal_instructions() {
  echo ""
  echo "=== Customer Portal ==="
  echo "Enable payment-method updates and invoice history:"
  echo "  https://dashboard.stripe.com/settings/billing/portal"
}

print_local_dev() {
  echo ""
  echo "=== Local development ==="
  echo "1. docker compose up --build"
  echo "2. In another terminal, forward webhooks (requires Stripe CLI):"
  echo "     stripe listen --forward-to ${LOCAL_WEBHOOK_URL}"
  echo "   Copy the whsec_... secret from that command into .env as STRIPE_WEBHOOK_SECRET."
  echo "3. Open http://localhost:8080 → Settings → Plan & billing → Upgrade"
  echo "4. Test card: 4242 4242 4242 4242 (any future expiry, any CVC)"
  if ! command -v stripe >/dev/null 2>&1; then
    echo ""
    echo "Stripe CLI not found. Install: brew install stripe/stripe-cli/stripe"
    echo "Or create a test webhook in the Dashboard pointing at a tunnel (ngrok) to ${LOCAL_WEBHOOK_URL}"
  fi
}

print_production_next() {
  echo ""
  echo "=== Production deploy ==="
  echo "1. Add GitHub Actions secrets (repo → Settings → Secrets):"
  echo "     STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRODUCT_ID"
  echo "2. Redeploy: ./scripts/deploy.sh --skip-tests"
  echo "3. Verify: curl -s https://www.mybetrecord.com/payments/health | jq"
}

main() {
  require_cmd curl
  load_secret_key

  if [[ "$STRIPE_SECRET_KEY" == sk_live_* || "$STRIPE_SECRET_KEY" == rk_live_* ]]; then
    echo "Using LIVE Stripe key — production account."
  else
    echo "Using TEST Stripe key — safe for local development."
  fi

  ENV_FILE="$ROOT/.env"
  DEPLOY_FILE="$ROOT/.env.deploy"

  ensure_product

  case "$MODE" in
    local)
      [[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"
      update_env_files local
      print_webhook_instructions "local (via Stripe CLI)" "$LOCAL_WEBHOOK_URL"
      print_local_dev
      ;;
    production)
      [[ -f "$DEPLOY_FILE" ]] || cp "$ROOT/.env.deploy.example" "$DEPLOY_FILE"
      update_env_files production
      print_webhook_instructions "production" "$PRODUCTION_WEBHOOK_URL"
      print_portal_instructions
      print_production_next
      if [[ "$RUN_DEPLOY" -eq 1 ]]; then
        echo ""
        echo "Deploying with updated Stripe settings..."
        "$ROOT/scripts/deploy.sh" --skip-tests
      fi
      ;;
    both)
      [[ -f "$ENV_FILE" ]] || cp "$ROOT/.env.example" "$ENV_FILE"
      [[ -f "$DEPLOY_FILE" ]] || cp "$ROOT/.env.deploy.example" "$DEPLOY_FILE"
      update_env_files local
      update_env_files production
      print_webhook_instructions "local (via Stripe CLI)" "$LOCAL_WEBHOOK_URL"
      print_webhook_instructions "production" "$PRODUCTION_WEBHOOK_URL"
      print_portal_instructions
      print_local_dev
      print_production_next
      ;;
  esac

  echo ""
  echo "Stripe account: https://dashboard.stripe.com/acct_1TmixlRrnbWHNbKP"
  echo "Product ID:     ${STRIPE_PRODUCT_ID}"
  echo ""
  echo "Integration is already in code (services/payments, Settings UI). Billing activates once"
  echo "STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are set and webhooks are registered."
}

main "$@"

#!/usr/bin/env bash
# Create (or update) the mybetrecord Stripe webhook via API — no Dashboard UI needed.
#
# Usage (from repo root):
#   ./scripts/setup_stripe_webhook.sh --production
#   ./scripts/setup_stripe_webhook.sh --production --replace   # delete + recreate (new whsec_)
#   ./scripts/setup_stripe_webhook.sh --production --deploy
#
# Reads STRIPE_SECRET_KEY from the environment or .env.deploy / .env.
# Writes STRIPE_WEBHOOK_SECRET to .env.deploy (production) or .env (local).
#
# Requires: curl, jq (recommended)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WEBHOOK_EVENTS=(
  checkout.session.completed
  customer.subscription.created
  customer.subscription.updated
  customer.subscription.deleted
)
PRODUCTION_WEBHOOK_URL="${PRODUCTION_WEBHOOK_URL:-https://www.mybetrecord.com/payments/webhook}"
LOCAL_WEBHOOK_URL="${LOCAL_WEBHOOK_URL:-http://localhost:8080/payments/webhook}"

MODE="production"
REPLACE=0
RUN_DEPLOY=0
ENDPOINT_ID=""

usage() {
  cat <<'EOF'
Create the mybetrecord Stripe webhook endpoint via API.

Options:
  --production    Target .env.deploy + production URL (default)
  --local         Target .env + local URL (usually use "stripe listen" instead)
  --replace       Delete an existing endpoint with the same URL, then recreate
                  (needed to obtain a new signing secret — Stripe only shows it once)
  --deploy        After updating .env.deploy, run ./scripts/deploy.sh --skip-tests
  -h, --help      Show this help

Environment:
  STRIPE_SECRET_KEY       Required (sk_live_... / rk_live_... or sk_test_...)
  PRODUCTION_WEBHOOK_URL  Override prod URL (default: https://www.mybetrecord.com/payments/webhook)

Examples:
  ./scripts/setup_stripe_webhook.sh --production
  ./scripts/setup_stripe_webhook.sh --production --replace --deploy

Note: Restricted keys (rk_live_...) need "Webhook endpoints" Write permission.
      If the API returns 403, use a secret key or update the restricted key permissions.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --production) MODE="production"; shift ;;
    --local) MODE="local"; shift ;;
    --replace) REPLACE=1; shift ;;
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
  for f in "$ROOT/.env.deploy" "$ROOT/.env"; do
    if [[ -f "$f" ]]; then
      local val
      val="$(grep -E '^STRIPE_SECRET_KEY=' "$f" | head -1 | cut -d= -f2- || true)"
      if [[ -n "$val" ]]; then
        STRIPE_SECRET_KEY="$val"
        return 0
      fi
    fi
  done
  echo "Set STRIPE_SECRET_KEY in .env.deploy or pass it in the environment." >&2
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

stripe_api_error() {
  local json="$1"
  if command -v jq >/dev/null 2>&1; then
    if echo "$json" | jq -e '.error' >/dev/null 2>&1; then
      echo "$json" | jq -r '.error | "\(.type): \(.message)"' >&2
      return 0
    fi
  elif echo "$json" | grep -q '"error"'; then
    echo "$json" >&2
    return 0
  fi
  return 1
}

upsert_env() {
  local file="$1" key="$2" value="$3"
  if [[ ! -f "$file" ]]; then
    cp "$ROOT/.env.deploy.example" "$file" 2>/dev/null || cp "$ROOT/.env.example" "$file" 2>/dev/null || touch "$file"
  fi
  if grep -q "^${key}=" "$file"; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

find_endpoint_id_for_url() {
  local target_url="$1"
  local list_json
  list_json="$(stripe_api GET /webhook_endpoints -G --data-urlencode "limit=100")"
  if stripe_api_error "$list_json"; then
    exit 1
  fi
  if command -v jq >/dev/null 2>&1; then
    echo "$list_json" | jq -r --arg u "$target_url" \
      '.data[] | select(.url == $u) | .id' | head -1
  else
    echo "jq is required to match existing webhook endpoints." >&2
    exit 1
  fi
}

delete_endpoint() {
  local endpoint_id="$1"
  echo "Deleting existing webhook endpoint ${endpoint_id}..."
  local del_json
  del_json="$(stripe_api DELETE "/webhook_endpoints/${endpoint_id}")"
  if stripe_api_error "$del_json"; then
    exit 1
  fi
  echo "Deleted ${endpoint_id}"
}

update_endpoint_events() {
  local endpoint_id="$1"
  local args=()
  for ev in "${WEBHOOK_EVENTS[@]}"; do
    args+=(-d "enabled_events[]=${ev}")
  done
  echo "Updating events on existing endpoint ${endpoint_id}..."
  local upd_json
  upd_json="$(stripe_api POST "/webhook_endpoints/${endpoint_id}" "${args[@]}")"
  if stripe_api_error "$upd_json"; then
    exit 1
  fi
  echo "Updated enabled events on ${endpoint_id}"
  echo ""
  echo "Stripe only returns the signing secret (whsec_...) when an endpoint is CREATED."
  echo "This endpoint already existed, so the secret was not returned."
  echo ""
  echo "Either:"
  echo "  1. Re-run with --replace to delete and recreate (generates a new whsec_)"
  echo "  2. Open Dashboard → Webhooks → your endpoint → Reveal signing secret"
  echo "     https://dashboard.stripe.com/webhooks"
  exit 0
}

create_endpoint() {
  local target_url="$1"
  local args=(
    --data-urlencode "url=${target_url}"
    -d "description=mybetrecord production billing webhook"
    -d "metadata[app]=mybetrecord"
  )
  for ev in "${WEBHOOK_EVENTS[@]}"; do
    args+=(-d "enabled_events[]=${ev}")
  done

  echo "Creating webhook endpoint: ${target_url}"
  echo "Events:"
  for ev in "${WEBHOOK_EVENTS[@]}"; do
    echo "  - ${ev}"
  done

  local create_json
  create_json="$(stripe_api POST /webhook_endpoints "${args[@]}")"
  if stripe_api_error "$create_json"; then
    echo ""
    echo "If you see a permissions error, your restricted key may need:"
    echo "  Webhook endpoints → Write"
    echo "Or use your account secret key (sk_live_...) for this one-time setup."
    exit 1
  fi

  local endpoint_id secret
  endpoint_id="$(echo "$create_json" | jq -r '.id')"
  secret="$(echo "$create_json" | jq -r '.secret // empty')"
  if [[ -z "$secret" || "$secret" == "null" ]]; then
    echo "Endpoint created (${endpoint_id}) but no signing secret in response." >&2
    echo "$create_json" >&2
    exit 1
  fi

  echo "Created endpoint: ${endpoint_id}"
  ENDPOINT_ID="$endpoint_id"
  STRIPE_WEBHOOK_SECRET="$secret"
}

main() {
  require_cmd curl
  require_cmd jq
  load_secret_key

  local env_file target_url
  case "$MODE" in
    production)
      env_file="$ROOT/.env.deploy"
      target_url="$PRODUCTION_WEBHOOK_URL"
      ;;
    local)
      env_file="$ROOT/.env"
      target_url="$LOCAL_WEBHOOK_URL"
      echo "Tip: for local dev, stripe listen is usually easier than a Dashboard webhook."
      echo "  stripe listen --forward-to ${LOCAL_WEBHOOK_URL}"
      echo ""
      ;;
  esac

  if [[ "$STRIPE_SECRET_KEY" == *live* ]]; then
    echo "Using LIVE Stripe key."
  else
    echo "Using TEST Stripe key."
  fi

  local existing_id
  existing_id="$(find_endpoint_id_for_url "$target_url" || true)"

  if [[ -n "$existing_id" && "$existing_id" != "null" ]]; then
    if [[ "$REPLACE" -eq 1 ]]; then
      delete_endpoint "$existing_id"
      create_endpoint "$target_url"
    else
      echo "Found existing endpoint for ${target_url}: ${existing_id}"
      update_endpoint_events "$existing_id"
    fi
  else
    create_endpoint "$target_url"
  fi

  upsert_env "$env_file" STRIPE_WEBHOOK_SECRET "$STRIPE_WEBHOOK_SECRET"
  echo ""
  echo "Wrote STRIPE_WEBHOOK_SECRET to ${env_file}"
  if [[ -z "$ENDPOINT_ID" ]]; then
    ENDPOINT_ID="$(find_endpoint_id_for_url "$target_url" || true)"
  fi
  echo "Webhook endpoint ID: ${ENDPOINT_ID}"
  echo ""
  echo "Next steps:"
  echo "  1. Add STRIPE_WEBHOOK_SECRET to GitHub Actions secrets (if using CI)"
  echo "  2. Deploy: ./scripts/deploy.sh --skip-tests"
  echo "  3. Verify: curl -s https://www.mybetrecord.com/payments/health"

  if [[ "$RUN_DEPLOY" -eq 1 ]]; then
    echo ""
    echo "Deploying..."
    "$ROOT/scripts/deploy.sh" --skip-tests
  fi
}

main "$@"

#!/usr/bin/env bash
# Deploy mybetrecord to Azure Container Apps.
#
# Usage (from repo root):
#   cp .env.deploy.example .env.deploy   # once — fill in secrets
#   ./scripts/deploy.sh                  # test, build images, deploy
#   ./scripts/deploy.sh --skip-tests     # deploy only
#   ./scripts/deploy.sh --bootstrap      # first-time: infra → images → infra
#
# Environment: loaded from .env.deploy (if present) and the shell.
# Requires: az CLI, logged-in Azure account with Contributor on the RG.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env.deploy" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env.deploy"
  set +a
fi

RESOURCE_GROUP="${RESOURCE_GROUP:-mybetrecord-rg}"
LOCATION="${LOCATION:-australiaeast}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short=7 HEAD 2>/dev/null || echo latest)}"
PARAMS_FILE="${PARAMS_FILE:-infra/main.parameters.json}"
BICEP_FILE="${BICEP_FILE:-infra/main.bicep}"
SERVICES=(auth bets reports payments)

SKIP_TESTS=0
BOOTSTRAP=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Deploy mybetrecord to Azure.

Options:
  --skip-tests     Skip pytest before deploy
  --bootstrap      First deploy: provision infra, push images, redeploy apps
  --dry-run        Print planned steps without executing az commands
  --tag TAG        Image tag (default: short git SHA, or "latest")
  -h, --help       Show this help

Required in .env.deploy or the environment:
  PG_ADMIN_PASSWORD
  JWT_SECRET

Optional:
  RESOURCE_GROUP, LOCATION, CORS_ORIGINS
  STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID
  AZURE_SUBSCRIPTION_ID (validates active subscription)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=1; shift ;;
    --bootstrap) BOOTSTRAP=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_var() {
  if [[ -z "${!1:-}" ]]; then
    echo "Missing required variable: $1 (set in .env.deploy or the environment)" >&2
    exit 1
  fi
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    echo "+ $*"
    "$@"
  fi
}

ensure_az() {
  if ! command -v az >/dev/null 2>&1; then
    echo "Azure CLI (az) is not installed. Install: https://learn.microsoft.com/cli/azure/install-azure-cli" >&2
    exit 1
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return
  fi
  if ! az account show >/dev/null 2>&1; then
    echo "Not logged in to Azure. Run: az login" >&2
    exit 1
  fi
  if [[ -n "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
    run az account set --subscription "$AZURE_SUBSCRIPTION_ID"
  fi
  echo "Azure subscription: $(az account show --query name -o tsv)"
}

run_tests() {
  if [[ "$SKIP_TESTS" -eq 1 ]]; then
    echo "Skipping tests (--skip-tests)."
    return
  fi
  echo "Running tests..."
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] pip install ./shared && pip install -r requirements-dev.txt && pytest -q"
    return
  fi
  python3 -m pip install -q ./shared
  python3 -m pip install -q -r requirements-dev.txt
  python3 -m pytest -q
}

ensure_resource_group() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    run az group create -n "$RESOURCE_GROUP" -l "$LOCATION"
    return
  fi
  if ! az group show -n "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
    run az group create -n "$RESOURCE_GROUP" -l "$LOCATION" -o none
  else
    echo "Resource group $RESOURCE_GROUP exists."
  fi
}

resolve_acr() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return
  fi
  ACR_NAME="$(az acr list -g "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || true)"
}

deploy_bicep() {
  local tag="$1"
  require_var PG_ADMIN_PASSWORD
  require_var JWT_SECRET

  local -a extra_params=(
    "imageTag=${tag}"
    "pgAdminPassword=${PG_ADMIN_PASSWORD}"
    "jwtSecret=${JWT_SECRET}"
  )
  if [[ -n "${CORS_ORIGINS:-}" ]]; then
    extra_params+=("corsOrigins=${CORS_ORIGINS}")
  fi
  if [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
    extra_params+=("stripeSecretKey=${STRIPE_SECRET_KEY}")
  fi
  if [[ -n "${STRIPE_WEBHOOK_SECRET:-}" ]]; then
    extra_params+=("stripeWebhookSecret=${STRIPE_WEBHOOK_SECRET}")
  fi
  if [[ -n "${STRIPE_PRICE_ID:-}" ]]; then
    extra_params+=("stripePriceId=${STRIPE_PRICE_ID}")
  fi

  run az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --name main \
    --template-file "$BICEP_FILE" \
    --parameters "$PARAMS_FILE" \
    --parameters "${extra_params[@]}"
}

build_and_push_images() {
  resolve_acr
  if [[ -z "${ACR_NAME:-}" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      ACR_NAME="<acr-from-infra>"
    else
      echo "No ACR in $RESOURCE_GROUP — run with --bootstrap or deploy infra first." >&2
      exit 1
    fi
  fi

  echo "Building images in ACR $ACR_NAME (tag: $IMAGE_TAG)..."
  for svc in "${SERVICES[@]}"; do
    run az acr build --registry "$ACR_NAME" \
      --image "${svc}:${IMAGE_TAG}" --image "${svc}:latest" \
      --file "services/${svc}/Dockerfile" .
  done
  run az acr build --registry "$ACR_NAME" \
    --image "frontend:${IMAGE_TAG}" --image "frontend:latest" \
    --file frontend/Dockerfile .
}

print_outputs() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    return
  fi
  local url
  url="$(az deployment group show \
    -g "$RESOURCE_GROUP" \
    -n main \
    --query "properties.outputs.frontendUrl.value" -o tsv 2>/dev/null || true)"
  if [[ -n "$url" ]]; then
    echo ""
    echo "Deployed. Frontend URL: $url"
  fi
}

# --- main ---
ensure_az
run_tests
ensure_resource_group

if [[ "$BOOTSTRAP" -eq 1 ]]; then
  echo "Bootstrap: provisioning infrastructure..."
  deploy_bicep "$IMAGE_TAG"
  build_and_push_images
  echo "Bootstrap: redeploying apps with images..."
  deploy_bicep "$IMAGE_TAG"
else
  resolve_acr
  if [[ -z "${ACR_NAME:-}" ]]; then
    echo "No ACR found — bootstrapping (infra → images → infra)..."
    deploy_bicep "$IMAGE_TAG"
    build_and_push_images
    deploy_bicep "$IMAGE_TAG"
  else
    build_and_push_images
    deploy_bicep "$IMAGE_TAG"
  fi
fi

print_outputs

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
INFRA_ONLY=0

usage() {
  cat <<'EOF'
Deploy mybetrecord to Azure.

Options:
  --skip-tests     Skip pytest before deploy
  --infra-only     Update Container Apps env/secrets only (no image rebuild)
  --bootstrap      First deploy: provision infra, push images, redeploy apps
  --dry-run        Print planned steps without executing az commands
  --tag TAG        Image tag (default: short git SHA, or "latest")
  -h, --help       Show this help

Required in .env.deploy or the environment:
  PG_ADMIN_PASSWORD
  JWT_SECRET

Optional:
  RESOURCE_GROUP, LOCATION, CORS_ORIGINS
  CUSTOM_HOSTNAMES (comma-separated, default: www.mybetrecord.com,mybetrecord.com)
  FRONTEND_APP (default: mybetrec-frontend)
  CONTAINERAPPS_ENV (default: derived from the frontend app)
  FRONTEND_URL (public site origin for password-reset links, e.g. https://www.mybetrecord.com)
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS
  STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRODUCT_ID
  FREE_WEEKLY_BET_LIMIT (max bets/week Mon–Sun on the free plan; default 5)
  AZURE_SUBSCRIPTION_ID (validates active subscription)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=1; shift ;;
    --infra-only) INFRA_ONLY=1; shift ;;
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

resolve_cors_origins() {
  if [[ -n "${CORS_ORIGINS:-}" && "${CORS_ORIGINS}" != "*" ]]; then
    return
  fi

  local -a origins=()
  add_origin() {
    local o="$1"
    [[ -z "$o" ]] && return
    local existing
    for existing in "${origins[@]}"; do
      [[ "$existing" == "$o" ]] && return
    done
    origins+=("$o")
  }

  if [[ -n "${FRONTEND_URL:-}" ]]; then
    add_origin "${FRONTEND_URL%/}"
  fi

  local hostnames="${CUSTOM_HOSTNAMES:-www.mybetrecord.com,mybetrecord.com}"
  local hostname
  IFS=',' read -ra hosts <<< "$hostnames"
  for hostname in "${hosts[@]}"; do
    hostname="${hostname#"${hostname%%[![:space:]]*}"}"
    hostname="${hostname%"${hostname##*[![:space:]]}"}"
    [[ -z "$hostname" ]] && continue
    add_origin "https://${hostname}"
  done

  if [[ ${#origins[@]} -eq 0 ]]; then
    return
  fi

  local IFS=,
  CORS_ORIGINS="${origins[*]}"
  echo "Resolved CORS_ORIGINS from FRONTEND_URL / CUSTOM_HOSTNAMES: ${CORS_ORIGINS}"
}

require_cors_for_production() {
  resolve_cors_origins
  if [[ "${CORS_ORIGINS:-}" == "*" || -z "${CORS_ORIGINS:-}" ]]; then
    local frontend="${FRONTEND_URL:-}"
    if [[ -z "$frontend" || "$frontend" == http://localhost* ]]; then
      return
    fi
    cat >&2 <<'EOF'
CORS_ORIGINS is '*' or unset for a production deploy.

Set CORS_ORIGINS in .env.deploy to your site origin(s), e.g.:
  CORS_ORIGINS=https://www.mybetrecord.com,https://mybetrecord.com

Or set FRONTEND_URL (and optionally CUSTOM_HOSTNAMES); deploy will derive origins automatically.
EOF
    exit 1
  fi
}

require_smtp_for_production() {
  if [[ -n "${SMTP_HOST:-}" ]]; then
    return
  fi
  local frontend="${FRONTEND_URL:-}"
  if [[ -z "$frontend" || "$frontend" == http://localhost* ]]; then
    return
  fi
  if [[ "${ALLOW_NO_SMTP:-}" == "1" ]]; then
    echo "WARNING: SMTP_HOST is unset; verification and password-reset emails will fail in production." >&2
    return
  fi
  cat >&2 <<'EOF'
Missing SMTP_HOST for a production deploy (FRONTEND_URL is set to a public site).

Signup verification and password-reset emails require SMTP on the auth service.
Set SMTP_* in .env.deploy (see .env.deploy.example) or run:

  ./scripts/setup_azure_email.sh

To deploy anyway without email, set ALLOW_NO_SMTP=1.
EOF
  exit 1
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

build_blog() {
  echo "Building blog and sitemap..."
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] python3 scripts/build_blog.py"
    return
  fi
  python3 -m pip install -q -r requirements-dev.txt
  python3 scripts/build_blog.py
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
  require_cors_for_production
  require_smtp_for_production

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
  if [[ -n "${STRIPE_PRODUCT_ID:-}" ]]; then
    extra_params+=("stripeProductId=${STRIPE_PRODUCT_ID}")
  fi
  if [[ -n "${FREE_WEEKLY_BET_LIMIT:-}" ]]; then
    extra_params+=("freeWeeklyBetLimit=${FREE_WEEKLY_BET_LIMIT}")
  fi
  if [[ -n "${FRONTEND_URL:-}" ]]; then
    extra_params+=("frontendUrl=${FRONTEND_URL}")
  fi
  if [[ -n "${SMTP_HOST:-}" ]]; then
    extra_params+=("smtpHost=${SMTP_HOST}")
  fi
  if [[ -n "${SMTP_PORT:-}" ]]; then
    extra_params+=("smtpPort=${SMTP_PORT}")
  fi
  if [[ -n "${SMTP_FROM:-}" ]]; then
    extra_params+=("smtpFrom=${SMTP_FROM}")
  fi
  if [[ -n "${SMTP_USE_TLS:-}" ]]; then
    extra_params+=("smtpUseTls=${SMTP_USE_TLS}")
  fi
  if [[ -n "${SMTP_USER:-}" ]]; then
    extra_params+=("smtpUser=${SMTP_USER}")
  fi
  if [[ -n "${SMTP_PASSWORD:-}" ]]; then
    extra_params+=("smtpPassword=${SMTP_PASSWORD}")
  fi

  run az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --name main \
    --template-file "$BICEP_FILE" \
    --parameters "$PARAMS_FILE" \
    --parameters "${extra_params[@]}"
}

deploy_bicep_with_retry() {
  local tag="$1"
  local attempt=1
  local max_attempts=30
  local wait_seconds=60

  while true; do
    local output
    if output="$(deploy_bicep "$tag" 2>&1)"; then
      [[ -n "$output" ]] && echo "$output"
      return 0
    fi
    echo "$output" >&2
    if [[ "$output" != *DeploymentActive* ]]; then
      return 1
    fi
    if (( attempt >= max_attempts )); then
      echo "Timed out waiting for the active Azure deployment to finish." >&2
      return 1
    fi
    echo "Another Azure deployment is in progress (attempt ${attempt}/${max_attempts}); retrying in ${wait_seconds}s..."
    sleep "$wait_seconds"
    attempt=$((attempt + 1))
  done
}

build_and_push_images() {
  build_blog
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
    --build-arg "BUILD_ID=${IMAGE_TAG}" \
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

bind_custom_hostnames() {
  local hostnames="${CUSTOM_HOSTNAMES:-www.mybetrecord.com,mybetrecord.com}"
  local frontend_app="${FRONTEND_APP:-mybetrec-frontend}"

  if [[ -z "$hostnames" ]]; then
    return
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] bind custom hostnames: $hostnames"
    return
  fi

  local env_name="${CONTAINERAPPS_ENV:-}"
  if [[ -z "$env_name" ]]; then
    local env_id
    env_id="$(az containerapp show \
      -g "$RESOURCE_GROUP" -n "$frontend_app" \
      --query properties.managedEnvironmentId -o tsv)"
    env_name="${env_id##*/}"
  fi

  echo "Ensuring custom hostnames on $frontend_app..."
  local hostname validation binding
  IFS=',' read -ra hosts <<< "$hostnames"
  for hostname in "${hosts[@]}"; do
    hostname="${hostname#"${hostname%%[![:space:]]*}"}"
    hostname="${hostname%"${hostname##*[![:space:]]}"}"
    [[ -z "$hostname" ]] && continue

    if [[ "$hostname" == www.* ]]; then
      validation="CNAME"
    else
      validation="HTTP"
    fi

    binding="$(az containerapp hostname list \
      -g "$RESOURCE_GROUP" -n "$frontend_app" \
      --query "[?name=='${hostname}'].bindingType | [0]" -o tsv 2>/dev/null || true)"

    if [[ -z "$binding" || "$binding" == "None" ]]; then
      run az containerapp hostname add \
        -g "$RESOURCE_GROUP" -n "$frontend_app" \
        --hostname "$hostname"
    fi

    if [[ "$binding" != "SniEnabled" ]]; then
      echo "Binding managed certificate for $hostname ($validation)..."
      run az containerapp hostname bind \
        -g "$RESOURCE_GROUP" -n "$frontend_app" \
        --hostname "$hostname" \
        --environment "$env_name" \
        --validation-method "$validation"
    else
      echo "Hostname already bound: $hostname"
    fi
  done
}

# --- main ---
ensure_az
run_tests
ensure_resource_group

if [[ "$INFRA_ONLY" -eq 1 ]]; then
  echo "Infra-only deploy (no image rebuild)..."
  deploy_bicep_with_retry "$IMAGE_TAG"
elif [[ "$BOOTSTRAP" -eq 1 ]]; then
  echo "Bootstrap: provisioning infrastructure..."
  deploy_bicep_with_retry "$IMAGE_TAG"
  build_and_push_images
  echo "Bootstrap: redeploying apps with images..."
  deploy_bicep_with_retry "$IMAGE_TAG"
else
  resolve_acr
  if [[ -z "${ACR_NAME:-}" ]]; then
    echo "No ACR found — bootstrapping (infra → images → infra)..."
    deploy_bicep_with_retry "$IMAGE_TAG"
    build_and_push_images
    deploy_bicep_with_retry "$IMAGE_TAG"
  else
    build_and_push_images
    deploy_bicep_with_retry "$IMAGE_TAG"
  fi
fi

print_outputs
bind_custom_hostnames

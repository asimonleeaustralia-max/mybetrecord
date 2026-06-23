#!/usr/bin/env bash
# Provision Azure Communication Services Email with SMTP for mybetrecord.
#
# Creates:
#   - Email Communication Service + Azure-managed sending domain
#   - Communication Service linked to that domain
#   - Entra app + SMTP username for smtp.azurecomm.net
#
# Writes SMTP_* and FRONTEND_URL into .env.deploy, then redeploys auth so
# verification emails are sent in production.
#
# Usage (from repo root):
#   ./scripts/setup_azure_email.sh
#   ./scripts/setup_azure_email.sh --skip-deploy
#
# Requires: az CLI (communication extension), logged-in Azure account.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RESOURCE_GROUP="${RESOURCE_GROUP:-mybetrecord-rg}"
LOCATION="${LOCATION:-australiaeast}"
EMAIL_SERVICE_NAME="${EMAIL_SERVICE_NAME:-mybetrec-email}"
COMM_SERVICE_NAME="${COMM_SERVICE_NAME:-mybetrec-comm}"
DOMAIN_NAME="AzureManagedDomain"
ENTRA_APP_NAME="${ENTRA_APP_NAME:-mybetrec-smtp}"
SMTP_USERNAME_RESOURCE="${SMTP_USERNAME_RESOURCE:-mybetrec-smtp-auth}"
SMTP_USERNAME_VALUE="${SMTP_USERNAME_VALUE:-mybetrec-mailer}"
FRONTEND_URL="${FRONTEND_URL:-https://www.mybetrecord.com}"
DATA_LOCATION="${DATA_LOCATION:-australia}"
SKIP_DEPLOY=0

usage() {
  cat <<'EOF'
Provision Azure Communication Services Email (SMTP) for mybetrecord.

Options:
  --skip-deploy   Only provision Azure resources and update .env.deploy
  -h, --help      Show this help

Environment overrides:
  RESOURCE_GROUP, EMAIL_SERVICE_NAME, COMM_SERVICE_NAME
  FRONTEND_URL, DATA_LOCATION
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-deploy) SKIP_DEPLOY=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_az() {
  command -v az >/dev/null || { echo "Azure CLI (az) is required." >&2; exit 1; }
  az account show >/dev/null 2>&1 || { echo "Run: az login" >&2; exit 1; }
}

ensure_extension() {
  if ! az extension show --name communication >/dev/null 2>&1; then
    echo "Installing Azure CLI communication extension..."
    az extension add --name communication --yes
  fi
  echo "Registering Microsoft.Communication provider (may take a minute)..."
  az provider register --namespace Microsoft.Communication --wait
}

resource_exists() {
  local kind="${1:-}" name="${2:-}"
  case "$kind" in
    email)
      az communication email show -g "$RESOURCE_GROUP" -n "$name" >/dev/null 2>&1
      ;;
    comm)
      az communication show -g "$RESOURCE_GROUP" -n "$name" >/dev/null 2>&1
      ;;
    domain)
      az communication email domain show -g "$RESOURCE_GROUP" \
        --email-service-name "$EMAIL_SERVICE_NAME" --domain-name "$DOMAIN_NAME" >/dev/null 2>&1
      ;;
    *)
      return 1
      ;;
  esac
}

create_email_service() {
  if resource_exists email "$EMAIL_SERVICE_NAME"; then
    echo "Email service $EMAIL_SERVICE_NAME already exists."
    return
  fi
  echo "Creating Email Communication Service: $EMAIL_SERVICE_NAME"
  az communication email create \
    -g "$RESOURCE_GROUP" \
    -n "$EMAIL_SERVICE_NAME" \
    --location global \
    --data-location "$DATA_LOCATION"
}

create_managed_domain() {
  if resource_exists domain; then
    echo "Azure managed domain already exists."
    return
  fi
  echo "Creating Azure-managed email domain..."
  az communication email domain create \
    -g "$RESOURCE_GROUP" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --domain-name "$DOMAIN_NAME" \
    --location global \
    --domain-management AzureManaged \
    --user-engmnt-tracking Disabled
}

wait_for_domain() {
  echo "Waiting for domain to become active..."
  local deadline=$((SECONDS + 600))
  while (( SECONDS < deadline )); do
    local status
    status="$(az communication email domain show \
      -g "$RESOURCE_GROUP" \
      --email-service-name "$EMAIL_SERVICE_NAME" \
      --domain-name "$DOMAIN_NAME" \
      --query "provisioningState" -o tsv 2>/dev/null || true)"
    if [[ "$status" == "Succeeded" ]]; then
      return 0
    fi
    sleep 10
  done
  echo "Timed out waiting for email domain provisioning." >&2
  exit 1
}

create_comm_service() {
  local domain_id
  domain_id="$(az communication email domain show \
    -g "$RESOURCE_GROUP" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --domain-name "$DOMAIN_NAME" \
    --query id -o tsv)"

  if resource_exists comm "$COMM_SERVICE_NAME"; then
    echo "Linking domain to existing Communication Service..."
    az communication update \
      -g "$RESOURCE_GROUP" \
      -n "$COMM_SERVICE_NAME" \
      --linked-domains "$domain_id"
    return
  fi

  echo "Creating Communication Service: $COMM_SERVICE_NAME"
  az communication create \
    -g "$RESOURCE_GROUP" \
    -n "$COMM_SERVICE_NAME" \
    --location global \
    --data-location "$DATA_LOCATION" \
    --linked-domains "$domain_id"
}

ensure_entra_app() {
  local app_id
  app_id="$(az ad app list --display-name "$ENTRA_APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)"
  if [[ -z "$app_id" || "$app_id" == "null" ]]; then
    echo "Creating Entra application: $ENTRA_APP_NAME"
    app_id="$(az ad app create --display-name "$ENTRA_APP_NAME" --query appId -o tsv)"
    az ad sp create --id "$app_id" >/dev/null
  else
    echo "Using existing Entra application: $ENTRA_APP_NAME ($app_id)"
    if ! az ad sp show --id "$app_id" >/dev/null 2>&1; then
      az ad sp create --id "$app_id" >/dev/null
    fi
  fi
  ENTRA_APP_ID="$app_id"
  TENANT_ID="$(az account show --query tenantId -o tsv)"
}

assign_role() {
  local scope="$1"
  local role="Communication and Email Service Owner"
  if az role assignment list --assignee "$ENTRA_APP_ID" --scope "$scope" --role "$role" --query "[0].id" -o tsv 2>/dev/null | grep -q .; then
    echo "Role already assigned to Entra app."
    return
  fi
  echo "Assigning $role to Entra app..."
  az role assignment create \
    --assignee "$ENTRA_APP_ID" \
    --role "$role" \
    --scope "$scope"
}

create_smtp_username() {
  local smtp_from_domain
  smtp_from_domain="$(az communication email domain show \
    -g "$RESOURCE_GROUP" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --domain-name "$DOMAIN_NAME" \
    --query "mailFromSenderDomain" -o tsv)"
  local smtp_user_email="DoNotReply@${smtp_from_domain}"

  if az communication smtp-username show \
    -g "$RESOURCE_GROUP" \
    --comm-service-name "$COMM_SERVICE_NAME" \
    --smtp-username "$SMTP_USERNAME_RESOURCE" >/dev/null 2>&1; then
    echo "SMTP username resource $SMTP_USERNAME_RESOURCE already exists."
    SMTP_USER="$smtp_user_email"
    return
  fi
  echo "Creating SMTP username..."
  az communication smtp-username create \
    -g "$RESOURCE_GROUP" \
    --comm-service-name "$COMM_SERVICE_NAME" \
    --smtp-username "$SMTP_USERNAME_RESOURCE" \
    --username "$smtp_user_email" \
    --entra-application-id "$ENTRA_APP_ID" \
    --tenant-id "$TENANT_ID"
  SMTP_USER="$smtp_user_email"
}

create_client_secret() {
  echo "Creating Entra client secret for SMTP authentication..."
  # credential reset returns the secret once; store it immediately.
  SMTP_PASSWORD="$(az ad app credential reset \
    --id "$ENTRA_APP_ID" \
    --display-name "mybetrec-smtp-$(date +%Y%m%d)" \
    --years 2 \
    --query password -o tsv)"
}

resolve_sender_address() {
  local from_domain
  from_domain="$(az communication email domain show \
    -g "$RESOURCE_GROUP" \
    --email-service-name "$EMAIL_SERVICE_NAME" \
    --domain-name "$DOMAIN_NAME" \
    --query "mailFromSenderDomain" -o tsv 2>/dev/null || true)"
  if [[ -z "$from_domain" || "$from_domain" == "null" ]]; then
    from_domain="$(az communication email domain show \
      -g "$RESOURCE_GROUP" \
      --email-service-name "$EMAIL_SERVICE_NAME" \
      --domain-name "$DOMAIN_NAME" \
      --query "fromSenderDomain" -o tsv 2>/dev/null || true)"
  fi
  if [[ -z "$from_domain" || "$from_domain" == "null" ]]; then
    from_domain="$(az communication email domain show \
      -g "$RESOURCE_GROUP" \
      --email-service-name "$EMAIL_SERVICE_NAME" \
      --domain-name "$DOMAIN_NAME" \
      --query "properties.fromSenderDomain" -o tsv 2>/dev/null || true)"
  fi
  if [[ -z "$from_domain" || "$from_domain" == "null" ]]; then
    echo "Could not resolve sender domain from Azure managed domain." >&2
    exit 1
  fi
  SMTP_FROM="DoNotReply@${from_domain}"
}

update_env_deploy() {
  local env_file="$ROOT/.env.deploy"
  if [[ ! -f "$env_file" ]]; then
    cp "$ROOT/.env.deploy.example" "$env_file"
  fi

  upsert_env() {
    local key="$1" value="$2"
    if grep -q "^${key}=" "$env_file"; then
      # macOS sed needs empty backup extension
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$env_file"
    else
      printf '%s=%s\n' "$key" "$value" >>"$env_file"
    fi
  }

  upsert_env FRONTEND_URL "$FRONTEND_URL"
  upsert_env SMTP_HOST smtp.azurecomm.net
  upsert_env SMTP_PORT 587
  upsert_env SMTP_USER "$SMTP_USER"
  upsert_env SMTP_PASSWORD "$SMTP_PASSWORD"
  upsert_env SMTP_FROM "$SMTP_FROM"
  upsert_env SMTP_USE_TLS true

  echo "Updated $env_file with SMTP settings (secret written locally; not committed)."
}

main() {
  require_az
  ensure_extension
  create_email_service
  create_managed_domain
  wait_for_domain
  create_comm_service

  local comm_scope
  comm_scope="$(az communication show -g "$RESOURCE_GROUP" -n "$COMM_SERVICE_NAME" --query id -o tsv)"

  ensure_entra_app
  assign_role "$comm_scope"
  create_smtp_username
  create_client_secret
  resolve_sender_address
  update_env_deploy

  cat <<EOF

Azure email setup complete.

  Email service:     $EMAIL_SERVICE_NAME
  Communication svc: $COMM_SERVICE_NAME
  SMTP host:         smtp.azurecomm.net:587
  SMTP user:         $SMTP_USER
  From address:      $SMTP_FROM
  Frontend URL:      $FRONTEND_URL

Next: redeploy so the auth service picks up SMTP settings.
EOF

  if [[ "$SKIP_DEPLOY" -eq 0 ]]; then
    echo "Applying SMTP settings to Container Apps..."
    "$ROOT/scripts/deploy.sh" --skip-tests --infra-only
  else
    echo "Skipped deploy (--skip-deploy). Run: ./scripts/deploy.sh --skip-tests"
  fi
}

main "$@"

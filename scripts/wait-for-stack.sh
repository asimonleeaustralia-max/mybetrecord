#!/usr/bin/env bash
# Wait until nginx can reach the auth service (used before e2e / Lighthouse in CI).
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1:8080}"
TIMEOUT="${WAIT_TIMEOUT:-180}"
deadline=$((SECONDS + TIMEOUT))

echo "Waiting for stack at ${BASE}/readyz (timeout ${TIMEOUT}s)…"
while (( SECONDS < deadline )); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/readyz" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    echo "Stack is ready."
    exit 0
  fi
  echo "  not ready yet (HTTP ${code})…"
  sleep 3
done

echo "Stack did not become ready within ${TIMEOUT}s." >&2
exit 1

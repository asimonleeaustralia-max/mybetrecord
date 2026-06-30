#!/usr/bin/env bash
# Wait until all compose services are healthy and nginx can reach auth (e2e / Lighthouse).
set -euo pipefail

BASE="${BASE_URL:-http://127.0.0.1:8080}"
TIMEOUT="${WAIT_TIMEOUT:-180}"
deadline=$((SECONDS + TIMEOUT))

SERVICES=(auth bets reports payments frontend)

service_health() {
  docker compose ps --status running --format '{{.Health}}' "$1" 2>/dev/null | head -1 || true
}

wait_for_compose_health() {
  echo "Waiting for compose services to become healthy (timeout ${TIMEOUT}s)…"
  while (( SECONDS < deadline )); do
    local all_ok=true
    for svc in "${SERVICES[@]}"; do
      health=$(service_health "$svc")
      case "$health" in
        healthy) ;;
        starting) all_ok=false ;;
        unhealthy)
          echo "Service ${svc} is unhealthy." >&2
          docker compose logs --no-color --tail=40 "$svc" >&2 || true
          return 1
          ;;
        *) all_ok=false ;;
      esac
    done
    if $all_ok; then
      echo "All services report healthy."
      return 0
    fi
    sleep 3
  done
  echo "Services did not become healthy within ${TIMEOUT}s." >&2
  docker compose ps -a >&2 || true
  return 1
}

wait_for_readyz() {
  echo "Waiting for stack at ${BASE}/readyz…"
  while (( SECONDS < deadline )); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/readyz" 2>/dev/null || echo "000")
    if [[ "$code" == "200" ]]; then
      echo "Stack is ready."
      return 0
    fi
    echo "  not ready yet (HTTP ${code})…"
    sleep 3
  done
  echo "Stack did not become ready within ${TIMEOUT}s." >&2
  return 1
}

wait_for_compose_health
wait_for_readyz

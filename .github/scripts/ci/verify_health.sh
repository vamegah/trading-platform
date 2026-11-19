#!/usr/bin/env bash
set -euo pipefail

API_URL="$1"
: "${API_URL:?API URL required}"

echo "Checking $API_URL/health"
for i in {1..20}; do
  if curl -fsS "$API_URL/health" >/dev/null; then
    echo "OK"
    exit 0
  fi
  sleep 10
done

echo "Health check failed" >&2
exit 1
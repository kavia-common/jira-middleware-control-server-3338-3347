#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3001}"
API_KEY="${API_KEY:-change-me-strong-key}"

echo "Health:"
curl -s "${BASE_URL}/health" | jq .

echo
echo "JIRA Search (requires valid env configuration and API key):"
curl -s -H "X-API-KEY: ${API_KEY}" \
  --get "${BASE_URL}/jira/search" \
  --data-urlencode "jql=project=PROJ ORDER BY created DESC" \
  --data-urlencode "max_results=5" | jq .

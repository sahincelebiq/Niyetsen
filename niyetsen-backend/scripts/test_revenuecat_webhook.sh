#!/usr/bin/env bash
# RevenueCat webhook'unu test eder (Railway env set edildikten sonra).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECRET_FILE="$ROOT/.railway-revenuecat-secret"
URL="${1:-https://api-production-86f1.up.railway.app/webhooks/revenuecat}"

if [[ ! -f "$SECRET_FILE" ]]; then
  echo "❌ .railway-revenuecat-secret bulunamadı"
  exit 1
fi
SECRET="$(tr -d '[:space:]' < "$SECRET_FILE")"

payload='{"event":{"type":"TEST","app_user_id":"webhook-smoke-user","expiration_at_ms":null}}'

code=$(curl -sS -o /tmp/rc-webhook-body.txt -w "%{http_code}" \
  -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${SECRET}" \
  -d "$payload")

echo "HTTP $code"
cat /tmp/rc-webhook-body.txt
echo ""

if [[ "$code" == "200" ]]; then
  echo "✅ Webhook doğrulaması OK"
else
  echo "❌ Beklenen 200 değil — Railway redeploy + REVENUECAT_WEBHOOK_SECRET kontrol et"
  exit 1
fi

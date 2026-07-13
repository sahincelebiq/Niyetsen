#!/usr/bin/env bash
# Railway prod env + redeploy (API servisi).
# Önkoşul: railway login (npx @railway/cli login)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CLI=(npx --yes @railway/cli@latest)

if ! "${CLI[@]}" whoami >/dev/null 2>&1; then
  echo "❌ Railway oturumu yok. Önce şunu çalıştır:"
  echo "   cd $ROOT && npx @railway/cli login"
  exit 1
fi

SECRET_FILE="$ROOT/.railway-revenuecat-secret"
if [[ ! -f "$SECRET_FILE" ]]; then
  openssl rand -hex 32 > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
fi
SECRET="$(tr -d '[:space:]' < "$SECRET_FILE")"

echo "→ Railway değişkenleri güncelleniyor (API servisi)…"
"${CLI[@]}" variable set ENV=prod --skip-deploys
"${CLI[@]}" variable set AUTH_DISABLED=false --skip-deploys
"${CLI[@]}" variable set USE_SUPABASE_DB=true --skip-deploys
"${CLI[@]}" variable set "REVENUECAT_WEBHOOK_SECRET=${SECRET}" --skip-deploys

echo "→ Redeploy başlatılıyor…"
"${CLI[@]}" redeploy --yes

echo ""
echo "✅ Tamam. Health kontrol:"
echo "   curl -sS https://api-production-86f1.up.railway.app/health"
echo ""
echo "⚠️  RevenueCat Authorization header (tam değer):"
echo "   Bearer ${SECRET}"
echo "   (Dosya: .railway-revenuecat-secret — gitignore'da)"

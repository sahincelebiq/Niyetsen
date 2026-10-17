#!/usr/bin/env bash
# niyetsen.com yayın paketi — ALLOWLIST (V2 §11 H5).
#
# Hostinger'a yalnız bu dizin yüklenir: website/_release/
#   scripts/build_release.sh            # paketi üret + içerik raporu
#   scripts/build_release.sh --check    # yasaklı dosya sızdı mı (CI/elle)
#
# Asla yüklenmez: build_legal_pages.py, vercel.json, .vercel/, .vercelignore,
# .env.local, .DS_Store, .gitignore, scripts/. (Bunlar Hostinger'da 200 dönüyordu.)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"
OUT="$HERE/_release"

ALLOW=(
  "*.html"
  "css/***" "js/***" "images/***" "fonts/***" "blog/***"
  "favicon.ico" "favicon.svg" "favicon-*.png" "apple-touch-icon.png"
  "robots.txt" "sitemap.xml" "llms.txt" "site.webmanifest"
  ".htaccess"
)
DENY_RE='(^|/)(\.env[^/]*|\.vercel(ignore)?(/|$)|vercel\.json|build_legal_pages\.py|.*\.py|\.DS_Store|\.gitignore|scripts/|_release/)'

if [[ "${1:-}" == "--check" ]]; then
  [[ -d "$OUT" ]] || { echo "önce paketi üret: scripts/build_release.sh"; exit 2; }
  if (cd "$OUT" && find . -type f | sed 's#^\./##' | grep -E "$DENY_RE"); then
    echo "HATA: yayın paketinde yasaklı dosya var"; exit 1
  fi
  echo "OK: yasaklı dosya yok ($(find "$OUT" -type f | wc -l | tr -d ' ') dosya)"
  exit 0
fi

rm -rf "$OUT"; mkdir -p "$OUT"
RSYNC_ARGS=(-a --prune-empty-dirs --exclude='_release/' --exclude='scripts/' --exclude='.vercel/' --exclude='.DS_Store')
for pattern in "${ALLOW[@]}"; do RSYNC_ARGS+=(--include="$pattern"); done
RSYNC_ARGS+=(--include='*/' --exclude='*')
rsync "${RSYNC_ARGS[@]}" "$HERE/" "$OUT/"

echo "yayın paketi: $OUT"
echo "  html: $(find "$OUT" -name '*.html' | wc -l | tr -d ' ')  toplam dosya: $(find "$OUT" -type f | wc -l | tr -d ' ')  boyut: $(du -sh "$OUT" | cut -f1)"
"$0" --check

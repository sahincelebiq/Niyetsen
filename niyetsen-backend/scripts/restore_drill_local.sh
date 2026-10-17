#!/usr/bin/env bash
# Haftalık geri yükleme tatbikatı — tek komut (V2 §7.1, KAPI 0).
#
#   scripts/restore_drill_local.sh                 # S3'ten en yeni dump'ı indir, yerel PG'ye restore, karşılaştır
#   scripts/restore_drill_local.sh --from-source   # kovasız: DIRECT_URL'den taze dump al, sonra tatbikat
#   scripts/restore_drill_local.sh --dump X.dump --manifest X.manifest.json
#
# Gereksinim: PostgreSQL 17 ikilileri (pg_dump/pg_restore/psql/initdb/pg_ctl).
#   macOS: brew install postgresql@17   (PATH: /opt/homebrew/opt/postgresql@17/bin)
#   Debian: postgresql-client-17 + postgresql-17
# Sunucu sürümü Supabase'de 17.x → pg_dump 17 şart (eski sürüm "server version mismatch" verir).
#
# Hedef: /tmp altında geçici, tek kullanımlık cluster (port 54329). Bitince silinir.
# Çıkış 0 = satır sayıları + md5 birebir (KAPI geçti).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

PG_BIN="${PG_BIN:-}"
if [[ -z "$PG_BIN" ]]; then
  for cand in /opt/homebrew/opt/postgresql@17/bin /usr/lib/postgresql/17/bin /usr/local/opt/postgresql@17/bin; do
    if [[ -x "$cand/initdb" ]]; then PG_BIN="$cand"; break; fi
  done
fi
if [[ -n "$PG_BIN" ]]; then export PATH="$PG_BIN:$PATH"; fi
for bin in initdb pg_ctl pg_restore psql pg_dump; do
  command -v "$bin" >/dev/null || { echo "HATA: $bin bulunamadı (PG_BIN=$PG_BIN)"; exit 2; }
done

PY="${PY:-$HERE/.venv/bin/python}"
[[ -x "$PY" ]] || PY=python3

MODE="fetch"
DUMP=""; MANIFEST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-source) MODE="source"; shift ;;
    --dump) DUMP="$2"; MODE="given"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    *) echo "bilinmeyen argüman: $1"; exit 2 ;;
  esac
done

WORK="$(mktemp -d /tmp/niyetsen-drill-XXXXXX)"
PORT="${DRILL_PORT:-54329}"
DATA="$WORK/pgdata"
TARGET_DSN="postgresql://niyetsen_drill@127.0.0.1:${PORT}/niyetsen_restore"
cleanup() {
  if [[ -f "$DATA/postmaster.pid" ]]; then pg_ctl -D "$DATA" stop -m fast -s >/dev/null 2>&1 || true; fi
  if [[ "${KEEP_DRILL:-}" != "1" ]]; then rm -rf "$WORK"; else echo "çalışma dizini korundu: $WORK"; fi
}
trap cleanup EXIT

echo "== 1/4 dump"
if [[ "$MODE" == "fetch" ]]; then
  "$PY" -m scripts.verify_backup fetch-latest --out-dir "$WORK"
  DUMP="$(ls "$WORK"/*.dump | head -1)"; MANIFEST="$DUMP.manifest.json"
elif [[ "$MODE" == "source" ]]; then
  # .env'i shell'e source etme (boşluklu değerler kırar); dotenv ile oku, ekrana yazma.
  SRC="${BACKUP_DATABASE_URL:-${DIRECT_URL:-}}"
  if [[ -z "$SRC" && -f .env ]]; then
    SRC="$("$PY" -c 'from dotenv import dotenv_values; v=dotenv_values(".env"); print(v.get("BACKUP_DATABASE_URL") or v.get("DIRECT_URL") or "")')"
  fi
  [[ -n "$SRC" ]] || { echo "HATA: BACKUP_DATABASE_URL / DIRECT_URL yok (.env veya ortam)"; exit 2; }
  SCHEMAS="${BACKUP_SCHEMAS:-$("$PY" -c 'from dotenv import dotenv_values; print(dotenv_values(".env").get("BACKUP_SCHEMAS") or "")' 2>/dev/null)}"
  DUMP="$WORK/source.dump"; MANIFEST="$DUMP.manifest.json"
  "$PY" -m scripts.verify_backup local-dump --dsn "$SRC" --out "$DUMP" ${SCHEMAS:+--schemas "$SCHEMAS"}
else
  [[ -f "$DUMP" && -f "${MANIFEST:-$DUMP.manifest.json}" ]] || { echo "HATA: dump/manifest bulunamadı"; exit 2; }
  MANIFEST="${MANIFEST:-$DUMP.manifest.json}"
fi

echo "== 2/4 geçici PostgreSQL 17 ($PORT)"
initdb -D "$DATA" -U niyetsen_drill --auth=trust -E UTF8 --locale=C >"$WORK/initdb.log" 2>&1
pg_ctl -D "$DATA" -o "-p $PORT -c listen_addresses=127.0.0.1 -c fsync=off -c synchronous_commit=off" -l "$WORK/pg.log" -w start >/dev/null
psql "postgresql://niyetsen_drill@127.0.0.1:${PORT}/postgres" -v ON_ERROR_STOP=1 -q -c "create database niyetsen_restore;"

echo "== 3/4 pg_restore + snapshot karşılaştırma"
set +e
"$PY" -m scripts.verify_backup drill --dump "$DUMP" --manifest "$MANIFEST" --target-dsn "$TARGET_DSN" \
  --target-snapshot-out "$WORK/target.snapshot.json"
RESULT=$?
set -e

echo "== 4/4 sonuç: $([[ $RESULT -eq 0 ]] && echo 'KAPI GEÇTİ ✅' || echo "KAPI GEÇMEDİ ❌ ($RESULT)")"
echo "tarih: $(date -u +%Y-%m-%dT%H:%M:%SZ)  dump: $(basename "$DUMP")  pg: $(pg_restore --version | awk '{print $3}')"
exit $RESULT

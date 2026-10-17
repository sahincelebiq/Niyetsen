#!/usr/bin/env bash
# Yerel vanilla PostgreSQL 17'de GERÇEK migration'ları koşar (Supabase stub'larıyla).
#
# İki iş görür:
#   1. Faz 7 §7.2/1 provası: migration dosyaları Supabase dışı Postgres'te koşuyor mu?
#      (hata veren satırlar = docs/SUPABASE_BAGIMLILIK.md adayı)
#   2. Yedek tatbikatı için "kaynak" stand-in: DB şifresi elde yokken
#      scripts/restore_drill_local.sh --from-source'u bu DSN ile koş.
#
#   scripts/local_pg_from_migrations.sh                 # cluster aç, migration + örnek veri, DSN yaz
#   scripts/local_pg_from_migrations.sh --stop          # cluster kapat
#   BACKUP_DATABASE_URL="$(scripts/local_pg_from_migrations.sh --dsn)" scripts/restore_drill_local.sh --from-source
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"
PG_BIN="${PG_BIN:-}"
if [[ -z "$PG_BIN" ]]; then
  for cand in /opt/homebrew/opt/postgresql@17/bin /usr/lib/postgresql/17/bin /usr/local/opt/postgresql@17/bin; do
    [[ -x "$cand/initdb" ]] && { PG_BIN="$cand"; break; }
  done
fi
[[ -n "$PG_BIN" ]] && export PATH="$PG_BIN:$PATH"

PORT="${STANDIN_PORT:-54330}"
DATA="${STANDIN_DATA:-/tmp/niyetsen-standin-pg}"
DSN="postgresql://niyetsen_src@127.0.0.1:${PORT}/niyetsen_src"

if [[ "${1:-}" == "--dsn" ]]; then echo "$DSN"; exit 0; fi
if [[ "${1:-}" == "--stop" ]]; then
  [[ -f "$DATA/postmaster.pid" ]] && pg_ctl -D "$DATA" stop -m fast -s || true
  rm -rf "$DATA"; echo "stand-in kapatıldı"; exit 0
fi

for bin in initdb pg_ctl psql; do command -v "$bin" >/dev/null || { echo "HATA: $bin yok (brew install postgresql@17)"; exit 2; }; done

if [[ ! -d "$DATA" ]]; then
  initdb -D "$DATA" -U niyetsen_src --auth=trust -E UTF8 --locale=C >/tmp/niyetsen-standin-initdb.log 2>&1
fi
if [[ ! -f "$DATA/postmaster.pid" ]]; then
  pg_ctl -D "$DATA" -o "-p $PORT -c listen_addresses=127.0.0.1 -c fsync=off" -l /tmp/niyetsen-standin-pg.log -w start >/dev/null
fi
psql "postgresql://niyetsen_src@127.0.0.1:${PORT}/postgres" -qAt -c "select 1 from pg_database where datname='niyetsen_src'" | grep -q 1 \
  || psql "postgresql://niyetsen_src@127.0.0.1:${PORT}/postgres" -q -c "create database niyetsen_src;"

echo "== Supabase stub'ları (roller, auth/storage şemaları, uid()/foldername())"
psql "$DSN" -q -v ON_ERROR_STOP=1 <<'SQL'
create schema if not exists extensions;
create extension if not exists "uuid-ossp" with schema extensions;
create extension if not exists pgcrypto with schema extensions;
do $$ declare r text; begin
  foreach r in array array['anon','authenticated','service_role','authenticator','supabase_admin','supabase_auth_admin','supabase_storage_admin','dashboard_user'] loop
    if not exists (select 1 from pg_roles where rolname = r) then execute format('create role %I nologin', r); end if;
  end loop; end $$;
create schema if not exists auth;
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text, raw_app_meta_data jsonb default '{}'::jsonb, raw_user_meta_data jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
create or replace function auth.uid() returns uuid language sql stable as
  $f$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $f$;
create or replace function auth.role() returns text language sql stable as
  $f$ select nullif(current_setting('request.jwt.claim.role', true), '') $f$;
create schema if not exists storage;
create table if not exists storage.buckets (
  id text primary key, name text not null, public boolean default false,
  file_size_limit bigint, allowed_mime_types text[], created_at timestamptz default now()
);
create table if not exists storage.objects (
  id uuid primary key default gen_random_uuid(), bucket_id text references storage.buckets(id),
  name text, owner uuid, metadata jsonb, created_at timestamptz default now()
);
alter table storage.objects enable row level security;
create or replace function storage.foldername(name text) returns text[] language sql immutable as
  $f$ select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'), 1) - 1] $f$;
SQL

echo "== migration'lar (sıralı; hata satırları aşağıda)"
ERRLOG=/tmp/niyetsen-standin-migrations.err; : > "$ERRLOG"
for f in supabase/migrations/2*.sql; do
  if ! psql "$DSN" -q -v ON_ERROR_STOP=0 -f "$f" 2>>"$ERRLOG" >/dev/null; then :; fi
done
ERRS=$(grep -c "ERROR" "$ERRLOG" || true)
echo "migration hata satırı: $ERRS  (ayrıntı: $ERRLOG)"
grep "ERROR" "$ERRLOG" | sed 's/^/  /' | sort | uniq -c | sort -rn | head -12 || true

echo "== örnek veri (idempotent)"
psql "$DSN" -q -v ON_ERROR_STOP=1 <<'SQL'
insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111','drill-a@niyetsen.test'),
  ('22222222-2222-2222-2222-222222222222','drill-b@niyetsen.test')
on conflict (id) do nothing;
insert into public.users (id, name, timezone) values
  ('11111111-1111-1111-1111-111111111111','Tatbikat A','Europe/Istanbul'),
  ('22222222-2222-2222-2222-222222222222','Tatbikat B','Europe/Berlin')
on conflict (id) do nothing;
insert into public.streaks (user_id, current_len, best_len) values
  ('11111111-1111-1111-1111-111111111111', 12, 23) on conflict (user_id) do nothing;
insert into public.points (user_id, category, value) values
  ('11111111-1111-1111-1111-111111111111','İrade',150),
  ('11111111-1111-1111-1111-111111111111','Disiplin',50),
  ('22222222-2222-2222-2222-222222222222','Sosyallik',100)
on conflict (user_id, category) do nothing;
insert into public.plans (id, user_id, duration_days, batch_generated_until, start_date) values
  ('plan-drill-a','11111111-1111-1111-1111-111111111111',365,7,current_date)
on conflict (id) do nothing;
insert into public.tasks (id, plan_id, day_no, title, categories) values
  ('task-drill-1','plan-drill-a',1,'10 dk yürüyüş','{İstikrar}'),
  ('task-drill-2','plan-drill-a',2,'Bir arkadaşı ara','{Sosyallik}'),
  ('task-drill-3','plan-drill-a',3,'Kitap 20 sayfa','{Disiplin}')
on conflict (id) do nothing;
SQL

TABLES=$(psql "$DSN" -qAt -c "select count(*) from information_schema.tables where table_schema in ('public','auth','storage') and table_type='BASE TABLE'")
echo "== hazır: $TABLES tablo (public+auth+storage)"
echo "DSN: $DSN"

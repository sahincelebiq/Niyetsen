/**
 * Niyetsen — SQL Editor TEK DOĞRULAMA PAKETİ (nizami, 2026-08-02)
 *
 * AMAÇ: Dashboard SQL Editor'da biriken Claude/Cursor yapıştırmalarını
 * TEKRAR ÇALIŞTIRMA. Bu dosya salt DOĞRULAMA sorgularıdır.
 *
 * Şema değişiklikleri → `supabase/migrations/*.sql` veya MCP apply_migration.
 * Eski "her şeyi create if not exists" yığını kaldırıldı; prod zaten uygulanmış.
 *
 * Kullanım: SQL Editor'a yapıştır → Run → sonuç tablolarını kontrol et.
 */

-- ============================================================
-- A) Tablolar + RLS (hepsi true olmalı; rls_off = 0)
-- ============================================================
select c.relname as table_name, c.relrowsecurity as rls_on
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by 1;

select count(*) as rls_disabled_tables
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
-- BEKLENEN: 0

-- ============================================================
-- B) Kritik kolonlar (eksik satır = sorun)
-- ============================================================
select t.col
from (
  values
    ('users','gender'),
    ('users','active_plan_id'),
    ('users','active_thread_id'),
    ('users','trial_started_at'),
    ('users','subscription_status'),
    ('users','notif_minute'),
    ('plans','name'),
    ('plans','slot_no'),
    ('chat_msgs','thread_id'),
    ('chat_msgs','plan_id'),
    ('push_tokens','last_tarot_push_date'),
    ('push_tokens','last_recap_push_date'),
    ('tasks','date'),
    ('tasks','tiny_version')
) as t(table_name, col)
where not exists (
  select 1 from information_schema.columns c
  where c.table_schema = 'public'
    and c.table_name = t.table_name
    and c.column_name = t.col
);
-- BEKLENEN: 0 satır

-- ============================================================
-- C) Kritik tablolar var mı
-- ============================================================
select t.tbl
from (
  values
    ('chat_threads'),
    ('fortune_log'),
    ('idol_personas'),
    ('persona_chunks'),
    ('proof_requests'),
    ('user_consents'),
    ('bonus_offers'),
    ('push_tokens')
) as t(tbl)
where not exists (
  select 1 from information_schema.tables x
  where x.table_schema = 'public' and x.table_name = t.tbl
);
-- BEKLENEN: 0 satır

-- ============================================================
-- D) RPC (service_role) — kanıt / bonus
-- ============================================================
select p.proname
from (
  values
    ('claim_proof_attempt'),
    ('finish_proof_attempt'),
    ('abort_proof_attempt'),
    ('complete_bonus_offer')
) as need(proname)
where not exists (
  select 1 from pg_proc pr
  join pg_namespace n on n.oid = pr.pronamespace
  where n.nspname = 'public' and pr.proname = need.proname
);
-- BEKLENEN: 0 satır

-- ============================================================
-- E) Storage bucket'ları
-- ============================================================
select id, name, public, file_size_limit
from storage.buckets
where id in ('proofs', 'plan-images')
order by 1;
-- BEKLENEN: proofs public=false; plan-images public=true

-- plan-images için geniş SELECT olmamalı (listing WARN)
select policyname
from pg_policies
where schemaname = 'storage'
  and policyname = 'plan_images_public_read';
-- BEKLENEN: 0 satır (2026-08-02'de kaldırıldı)

-- ============================================================
-- F) Tablo policy sayısı (bilinçli: 0 = deny-by-default + backend service_role)
-- ============================================================
select t.tablename,
  (select count(*) from pg_policies p
   where p.schemaname = 'public' and p.tablename = t.tablename) as policy_count
from pg_tables t
where t.schemaname = 'public'
order by 1;
-- BEKLENEN: çoğu 0 (anon/authenticated PostgREST'ten kapalı; FastAPI service_role)

-- ============================================================
-- G) Gender check
-- ============================================================
select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.users'::regclass
  and conname = 'users_gender_check';
-- BEKLENEN: kadın | erkek | belirtmek istemiyorum

-- VERIFY: preferred_language (Play i18n)
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users' and column_name = 'preferred_language';

-- ============================================================
-- H) faz8.13/4 — Lig tablosu (league_members)
-- Önce migration'ı uygula: 20260810120000_faz813_league_members.sql
-- ============================================================
create table if not exists public.league_members (
  user_id uuid primary key references auth.users (id) on delete cascade,
  alias text not null check (char_length(alias) between 2 and 24),
  score integer not null default 0 check (score >= 0),
  streak integer not null default 0 check (streak >= 0),
  updated_at timestamptz not null default now()
);
create index if not exists league_members_score_idx
  on public.league_members (score desc, streak desc);
alter table public.league_members enable row level security;

-- VERIFY: league_members var + RLS açık + policy 0 (deny-by-default)
select relname, relrowsecurity
from pg_class
where relnamespace = 'public'::regnamespace and relname = 'league_members';
-- BEKLENEN: 1 satır, relrowsecurity = true

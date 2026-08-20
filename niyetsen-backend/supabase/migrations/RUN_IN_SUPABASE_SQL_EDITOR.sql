-- Niyetsen — SQL Editor TEK DOĞRULAMA PAKETİ (nizami, 2026-08-13)
--
-- AMAÇ: Dashboard'daki 33 kayıtlı sorguyu TEKRAR ÇALIŞTIRMA.
-- Bu dosya salt DOĞRULAMA'dır (bölüm I hariç — o bir kez güvenlik).
--
-- SQL Editor'da ÇALIŞTIRMA (DDL / backfill — şema zaten prod'da):
--   Toplu şema, idol persona, İdol Modu persona dosyaları,
--   chat_threads (+ backfill), faz 8 kadın erkek algılaması,
--   Untitled fortune_log CREATE, last_tarot_push_date ALTER.
--
-- Güvenli (bu dosyanın A–H kopyaları): RLS, kritik tablo/kolon, RPC,
--   storage, policy sayıları, cinsiyet + dil.
--
-- Kullanım: A–H'yi yapıştır → Run. Beklenen: eksik satır yok, rls_off=0.
-- I yalnız bir kez: anon GRANT kapatma (PostgREST savunması).
--
-- NOT: Başlık çift tire. Eski /** */ iç içe yorum = 42601.

-- ============================================================
-- A) Tablolar + RLS (hepsi true; rls_off = 0)
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
    ('users','preferred_language'),
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
    ('push_tokens'),
    ('league_members')
) as t(tbl)
where not exists (
  select 1 from information_schema.tables x
  where x.table_schema = 'public' and x.table_name = t.tbl
);
-- BEKLENEN: 0 satır

-- ============================================================
-- D) RPC (service_role) — kanıt / bonus
-- ============================================================
select need.proname
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

select policyname
from pg_policies
where schemaname = 'storage'
  and policyname = 'plan_images_public_read';
-- BEKLENEN: 0 satır (2026-08-02'de kaldırıldı)

-- ============================================================
-- F) Tablo policy sayısı (0 = deny-by-default + backend service_role)
-- ============================================================
select t.tablename,
  (select count(*) from pg_policies p
   where p.schemaname = 'public' and p.tablename = t.tablename) as policy_count
from pg_tables t
where t.schemaname = 'public'
order by 1;
-- BEKLENEN: hepsi 0

-- ============================================================
-- G) Gender + dil + fal tipi (kayıtlı sorgulardaki 'Tarot' YANLIŞ)
-- ============================================================
select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.users'::regclass
  and conname = 'users_gender_check';
-- BEKLENEN: kadın | erkek | belirtmek istemiyorum

select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name = 'preferred_language';
-- BEKLENEN: 1 satır, text

select pg_get_constraintdef(oid) as fortune_type_check
from pg_constraint
where conrelid = 'public.fortune_log'::regclass
  and conname = 'fortune_log_type_check';
-- BEKLENEN: tarot | kahve | el | burc  (büyük T 'Tarot' DEĞİL)

-- ============================================================
-- H) Lig tablosu — yalnız doğrula (CREATE yok; tablo prod'da var)
-- ============================================================
select relname, relrowsecurity
from pg_class
where relnamespace = 'public'::regnamespace and relname = 'league_members';
-- BEKLENEN: 1 satır, relrowsecurity = true

-- ============================================================
-- I) BİR KEZ — anon/authenticated GRANT kapat (PostgREST savunması)
-- RLS policy=0 satırları keser; GRANT ALL (TRUNCATE dahil) yine yüzey.
-- A–H yeşil kaldıktan sonra AYRI çalıştır. Tekrar çalıştırmak güvenli.
-- ============================================================
-- revoke all on all tables in schema public from anon, authenticated;
-- revoke all on all sequences in schema public from anon, authenticated;
-- alter default privileges in schema public
--   revoke all on tables from anon, authenticated;
-- alter default privileges in schema public
--   revoke all on sequences from anon, authenticated;
--
-- select count(*) as leftover_grants
-- from information_schema.role_table_grants
-- where table_schema = 'public'
--   and grantee in ('anon', 'authenticated');
-- BEKLENEN leftover_grants: 0  (2026-08-20 uygulandı)

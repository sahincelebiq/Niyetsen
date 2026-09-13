-- Niyetsen — SQL Editor TEK DOĞRULAMA PAKETİ (36 başlık, 2026-09-13)
--
-- AMAÇ: Dashboard Private'daki eski Untitled / DDL snippet'lerini
-- TEKRAR ÇALIŞTIRMA. Bu dosya salt DOĞRULAMA'dır.
--
-- SQL Editor'da ÇALIŞTIRMA (şema zaten prod'da):
--   Toplu CREATE, idol seed, chat_threads backfill, Untitled fortune_log,
--   last_tarot_push_date ALTER, rastgele policy ekleme.
--
-- Kullanım: 01–36'yı tek tek Run. Beklenen: eksik satır yok, rls_off=0.
-- Nested /* */ yorum YASAK (42601). Başlık = çift tire.

-- ============================================================
-- 01) RLS açık tablolar (hepsi true)
-- ============================================================
select c.relname as table_name, c.relrowsecurity as rls_on
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by 1;

-- ============================================================
-- 02) RLS kapalı tablo sayısı
-- ============================================================
select count(*) as rls_disabled_tables
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
-- BEKLENEN: 0

-- ============================================================
-- 03) Kritik kolonlar (eksik satır = sorun)
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
    ('tasks','tiny_version'),
    ('chat_threads','kind'),
    ('plan_events','plan_id'),
    ('plan_events','task_id'),
    ('plan_events','deleted_at'),
    ('plan_events','remind_offset_min'),
    ('plan_event_occurrences','event_id'),
    ('plan_event_occurrences','scheduled_at'),
    ('plan_event_occurrences','remind_at'),
    ('plan_event_occurrences','points_source'),
    ('point_log','kind'),
    ('point_log','source_kind'),
    ('point_log','source_id'),
    ('plan_step_notes','body')
) as t(table_name, col)
where not exists (
  select 1 from information_schema.columns c
  where c.table_schema = 'public'
    and c.table_name = t.table_name
    and c.column_name = t.col
);
-- BEKLENEN: 0 satır

-- ============================================================
-- 04) Kritik tablolar var mı
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
    ('league_members'),
    ('plan_events'),
    ('plan_event_occurrences'),
    ('plan_step_notes')
) as t(tbl)
where not exists (
  select 1 from information_schema.tables x
  where x.table_schema = 'public' and x.table_name = t.tbl
);
-- BEKLENEN: 0 satır

-- ============================================================
-- 05) RPC (service_role) — kanıt / bonus
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
-- 06) Storage bucket'ları
-- ============================================================
select id, name, public, file_size_limit
from storage.buckets
where id in ('proofs', 'plan-images')
order by 1;
-- BEKLENEN: proofs public=false; plan-images public=true

-- ============================================================
-- 07) Kaldırılmış plan-images listing policy
-- ============================================================
select policyname
from pg_policies
where schemaname = 'storage'
  and policyname = 'plan_images_public_read';
-- BEKLENEN: 0 satır (2026-08-02'de kaldırıldı)

-- ============================================================
-- 08) Tablo policy sayısı (0 = deny-by-default + backend service_role)
-- ============================================================
select t.tablename,
  (select count(*) from pg_policies p
   where p.schemaname = 'public' and p.tablename = t.tablename) as policy_count
from pg_tables t
where t.schemaname = 'public'
order by 1;
-- BEKLENEN: hepsi 0

-- ============================================================
-- 09) Cinsiyet kısıtı (kayıtlı sorgulardaki 'Tarot' / 'kadın-erkek' YANLIŞ)
-- ============================================================
select conname, pg_get_constraintdef(oid) as def
from pg_constraint
where conrelid = 'public.users'::regclass
  and conname = 'users_gender_check';
-- BEKLENEN: kadın | erkek | belirtmek istemiyorum

-- ============================================================
-- 10) Tercih edilen dil
-- ============================================================
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name = 'preferred_language';
-- BEKLENEN: 1 satır, text

-- ============================================================
-- 11) Fal tipi (chat dahil)
-- ============================================================
select pg_get_constraintdef(oid) as fortune_type_check
from pg_constraint
where conrelid = 'public.fortune_log'::regclass
  and conname = 'fortune_log_type_check';
-- BEKLENEN: tarot | kahve | el | burc | chat

-- ============================================================
-- 12) Anon / authenticated GRANT artığı
-- ============================================================
select count(*) as leftover_grants
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated');
-- BEKLENEN: 0

-- ============================================================
-- 13) Lig tablosu
-- ============================================================
select relname, relrowsecurity
from pg_class
where relnamespace = 'public'::regnamespace and relname = 'league_members';
-- BEKLENEN: 1 satır, relrowsecurity = true

-- ============================================================
-- 14) chat_threads kolonları
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'chat_threads'
order by ordinal_position;
-- BEKLENEN: id, user_id, plan_id, title, created_at, updated_at

-- ============================================================
-- 15) İdol persona tohumu
-- ============================================================
select count(*)::int as idol_rows
from public.idol_personas;
-- BEKLENEN: 10 (DB tohumu). Dosya yedeği 18 yol (Gaia + Kozmos dahil).

-- ============================================================
-- 16) persona_chunks (0 = dosya fallback; zorunlu değil)
-- ============================================================
select count(*)::int as chunk_rows
from public.persona_chunks;
-- BEKLENEN: 0 veya daha fazla; 0 ise ingest_personas.py yedeği çalışır

-- ============================================================
-- 17) FAZ 8 covering index'ler
-- ============================================================
select t.idx
from (
  values
    ('chat_msgs_plan_id_idx'),
    ('chat_threads_plan_id_idx'),
    ('intents_plan_id_idx'),
    ('point_log_task_id_idx'),
    ('tasks_proof_id_idx'),
    ('users_active_plan_id_idx'),
    ('users_active_thread_id_idx')
) as t(idx)
where not exists (
  select 1 from pg_indexes i
  where i.schemaname = 'public' and i.indexname = t.idx
);
-- BEKLENEN: 0 satır

-- ============================================================
-- 18) Cron / görev indeksleri
-- ============================================================
select t.idx
from (
  values
    ('tasks_date_pending_idx'),
    ('tasks_date_status_idx'),
    ('tasks_plan_date_idx'),
    ('chat_threads_user_updated_idx')
) as t(idx)
where not exists (
  select 1 from pg_indexes i
  where i.schemaname = 'public' and i.indexname = t.idx
);
-- BEKLENEN: 0 satır

-- ============================================================
-- 19) Storage policy (kanıt yazma kapalı; yalnız own SELECT)
-- ============================================================
select policyname, cmd
from pg_policies
where schemaname = 'storage'
order by 1;
-- BEKLENEN: yalnız proofs_select_own / SELECT
-- YOK: proofs_insert_own, proofs_update_own, proofs_delete_own

-- ============================================================
-- 20) users.notif_minute
-- ============================================================
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name = 'notif_minute';
-- BEKLENEN: 1 satır

-- ============================================================
-- 21) users.subscription_status
-- ============================================================
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name = 'subscription_status';
-- BEKLENEN: 1 satır

-- ============================================================
-- 22) users.trial_started_at
-- ============================================================
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name = 'trial_started_at';
-- BEKLENEN: 1 satır

-- ============================================================
-- 23) Aktif plan + aktif thread
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'users'
  and column_name in ('active_plan_id', 'active_thread_id')
order by 1;
-- BEKLENEN: 2 satır

-- ============================================================
-- 24) tasks.date + tiny_version (kanıt bağlamı)
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'tasks'
  and column_name in ('date', 'tiny_version')
order by 1;
-- BEKLENEN: 2 satır

-- ============================================================
-- 25) Push: tarot + rapor tarihi
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'push_tokens'
  and column_name in ('last_tarot_push_date', 'last_recap_push_date')
order by 1;
-- BEKLENEN: 2 satır

-- ============================================================
-- 26) plans.name + slot_no (çoklu plan)
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'plans'
  and column_name in ('name', 'slot_no')
order by 1;
-- BEKLENEN: 2 satır

-- ============================================================
-- 27) chat_msgs.thread_id + plan_id
-- ============================================================
select column_name
from information_schema.columns
where table_schema = 'public' and table_name = 'chat_msgs'
  and column_name in ('thread_id', 'plan_id')
order by 1;
-- BEKLENEN: 2 satır

-- ============================================================
-- 28) fortune_log.type değerleri (chat şart)
-- ============================================================
select pg_get_constraintdef(oid) as fortune_type_check
from pg_constraint
where conrelid = 'public.fortune_log'::regclass
  and conname = 'fortune_log_type_check';
-- BEKLENEN: içinde 'chat' geçer

-- ============================================================
-- 29) proof_requests tablosu
-- ============================================================
select 1 as ok
from information_schema.tables
where table_schema = 'public' and table_name = 'proof_requests';
-- BEKLENEN: 1 satır

-- ============================================================
-- 30) user_consents tablosu
-- ============================================================
select 1 as ok
from information_schema.tables
where table_schema = 'public' and table_name = 'user_consents';
-- BEKLENEN: 1 satır

-- ============================================================
-- 31) bonus_offers tablosu
-- ============================================================
select 1 as ok
from information_schema.tables
where table_schema = 'public' and table_name = 'bonus_offers';
-- BEKLENEN: 1 satır

-- ============================================================
-- 32) Gerekli eklentiler
-- ============================================================
select extname
from pg_extension
where extname in ('pgcrypto', 'uuid-ossp', 'plpgsql', 'pg_stat_statements')
order by 1;
-- BEKLENEN: 4 satır

-- ============================================================
-- 33) Uygulanmış migration kayıtları
-- ============================================================
select version, name
from supabase_migrations.schema_migrations
order by version;
-- BEKLENEN: gender, recap, normalize, preferred_language,
--           revoke grants, fortune_log chat type,
--           plan_events_agent, plan_events_point_log_fk,
--           plan_step_events, plan_event_occurrences_fill_schedule

-- ============================================================
-- 34) plans.id TEXT (uuid değil — 42804 tuzağı)
-- ============================================================
select data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'plans' and column_name = 'id';
-- BEKLENEN: text

-- ============================================================
-- 35) Özet — hepsi yeşil mi?
-- ============================================================
select
  (select count(*) from pg_class c
   join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity
  ) as rls_off,
  (select count(*) from information_schema.role_table_grants
   where table_schema = 'public' and grantee in ('anon', 'authenticated')
  ) as leftover_grants,
  (select count(*) from public.idol_personas) as idol_rows,
  (select public from storage.buckets where id = 'proofs') as proofs_public,
  (select public from storage.buckets where id = 'plan-images') as plan_images_public;
-- BEKLENEN: rls_off=0, leftover_grants=0, idol_rows=10 (DB tohumu),
--           proofs_public=false, plan_images_public=true

-- ============================================================
-- 36) Plan → Etkinlik → Puan hattı (2026-09-13, migration plan_step_events)
-- ============================================================
-- 36a) İndeksler + tetikleyiciler (eksik satır = sorun)
select need.obj
from (
  values
    ('idx:plan_events_task_active_uniq'),
    ('idx:plan_events_task_id_idx'),
    ('idx:plan_events_user_active_idx'),
    ('idx:plan_event_occurrences_remind_due_idx'),
    ('idx:plan_event_occurrences_user_status_date_idx'),
    ('idx:point_log_complete_once_uniq'),
    ('idx:point_log_source_idx'),
    ('idx:plan_step_notes_task_id_idx'),
    ('trg:point_log_fill_source_trg'),
    ('trg:plan_event_occurrences_fill_trg')
) as need(obj)
where not exists (
  select 1 from pg_indexes i
  where i.schemaname = 'public' and 'idx:' || i.indexname = need.obj
)
and not exists (
  select 1 from pg_trigger t
  where not t.tgisinternal and 'trg:' || t.tgname = need.obj
);
-- BEKLENEN: 0 satır

-- 36b) Puan defteri sınıflandırması + çift tamamlama yok
select
  (select count(*) from public.point_log where kind is null or source_kind is null) as unfilled_rows,
  (select count(*) from (
     select source_kind, source_id, category
     from public.point_log where kind = 'complete'
     group by 1, 2, 3 having count(*) > 1
   ) d) as duplicate_completions,
  (select count(*) from public.plan_event_occurrences where scheduled_at is null) as occ_without_utc,
  (select count(*) from public.plan_events where task_id is not null and deleted_at is null) as step_linked_active_events;
-- BEKLENEN: unfilled_rows=0, duplicate_completions=0, occ_without_utc=0

-- 36c) Olay durumu 4 değer
select pg_get_constraintdef(oid)
from pg_constraint where conname = 'plan_event_occurrences_status_check';
-- BEKLENEN: pending, done, skipped, missed

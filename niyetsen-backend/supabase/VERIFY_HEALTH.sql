-- Niyetsen — Supabase sağlık kontrolü (YALNIZCA OKUMA)
-- SQL Editor'da çalıştır; "destructive" uyarısı ÇIKMAMALI.

-- 1) Gerekli tablolar
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'users', 'streaks', 'points', 'plans', 'tasks', 'chat_msgs', 'intents',
    'proofs', 'point_log', 'push_tokens', 'bonus_offers', 'user_consents',
    'proof_requests'
  )
order by table_name;

-- 2) users kritik kolonlar
select column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'users'
  and column_name in (
    'active_plan_id', 'trial_started_at', 'subscription_expires_at',
    'timezone', 'subscription_status'
  )
order by column_name;

-- 3) plans çoklu-slot
select column_name
from information_schema.columns
where table_schema = 'public'
  and table_name = 'plans'
  and column_name in ('name', 'slot_no')
order by column_name;

-- 4) Veri bütünlüğü
select
  (select count(*) from public.users) as users,
  (select count(*) from public.streaks) as streaks,
  (select count(*) from public.users u
     left join public.streaks s on s.user_id = u.id
     where s.user_id is null) as users_without_streak,
  (select count(*) from public.tasks
     where categories is null or cardinality(categories) = 0) as tasks_bad_categories,
  (select count(*) from public.plans) as plans;

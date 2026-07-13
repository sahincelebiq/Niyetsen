-- =============================================================================
-- NİYETSEN — Supabase SQL Editor (PROD güncelleme)
-- =============================================================================
-- ÖNEMLİ: Dosya yolunu DEĞİL, bu dosyanın İÇERİĞİNİ yapıştır.
-- Yanlış: niyetsen-backend/supabase/migrations/RUN_IN_SUPABASE_SQL_EDITOR.sql
-- Doğru:  Aşağıdaki SQL satırlarının tamamı
--
-- "Destructive operations" uyarısı normaldir (constraint drop + veri onarımı).
-- Uygulama verisini silmez; yalnızca şema tamamlar ve bozuk satırları düzeltir.
-- =============================================================================

-- FAZ 5+: çoklu plan projeleri (abonelikle 2+ plan; free/trial = 1 plan)
alter table public.plans drop constraint if exists plans_user_id_key;

alter table public.plans
  add column if not exists name text not null default 'Planım',
  add column if not exists slot_no int not null default 1;

create unique index if not exists plans_user_slot_idx
  on public.plans(user_id, slot_no);

alter table public.users
  add column if not exists active_plan_id text references public.plans(id) on delete set null;

alter table public.intents
  add column if not exists plan_id text references public.plans(id) on delete set null;

alter table public.chat_msgs
  add column if not exists plan_id text references public.plans(id) on delete set null;

create index if not exists chat_msgs_user_plan_idx
  on public.chat_msgs(user_id, plan_id, created_at);

-- FAZ 5: deneme süresi (sohbet /chat bu kolona bakar — eksikse 500 verir)
alter table public.users
  add column if not exists trial_started_at timestamptz;

-- FAZ 5+: iptal sonrası dönem sonu (RevenueCat expiration_at)
alter table public.users
  add column if not exists subscription_expires_at timestamptz;

-- Veri onarımı: cron close-day için categories boş/null olmamalı
update public.tasks
set categories = array['İrade']::text[]
where categories is null or cardinality(categories) = 0;

-- Eksik streak satırları (cron list_cron_users → get_state)
insert into public.streaks (user_id, current_len, best_len, silent_miss_streak)
select u.id, 0, 0, 0
from public.users u
left join public.streaks s on s.user_id = u.id
where s.user_id is null
on conflict (user_id) do nothing;

/**
 * Supabase SQL Editor'da çalıştırılacak migration.
 * NOT: Python test dosyası DEĞİL — yalnızca bu SQL'i yapıştır.
 */
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

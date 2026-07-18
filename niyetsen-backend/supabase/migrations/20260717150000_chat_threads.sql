-- FAZ 7.6: Sohbet oturumları (Claude tarzı) — yeni sohbet ESKİYİ SİLMEZ.
-- Her oturumun başlığı vardır; sol panelde geçmiş sohbetler listelenir.
-- Pazarlama/retention verisi korunur (Şahin'in kararı, 2026-07-17).

create table if not exists public.chat_threads (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  plan_id uuid references public.plans(id) on delete set null,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists chat_threads_user_updated_idx
  on public.chat_threads(user_id, updated_at desc);

alter table public.chat_threads enable row level security;

alter table public.chat_msgs
  add column if not exists thread_id uuid references public.chat_threads(id) on delete cascade;

create index if not exists chat_msgs_thread_idx
  on public.chat_msgs(thread_id, created_at);

alter table public.users
  add column if not exists active_thread_id uuid;

-- Backfill: mevcut mesajlar (thread_id NULL) plan başına tek "geçmiş" oturuma
-- toplanır — hiçbir eski sohbet kaybolmaz.
insert into public.chat_threads (user_id, plan_id, title, created_at, updated_at)
select m.user_id, m.plan_id, 'Önceki sohbet', min(m.created_at), max(m.created_at)
from public.chat_msgs m
where m.thread_id is null
group by m.user_id, m.plan_id;

update public.chat_msgs m
set thread_id = t.id
from public.chat_threads t
where m.thread_id is null
  and t.user_id = m.user_id
  and (t.plan_id = m.plan_id or (t.plan_id is null and m.plan_id is null))
  and t.title = 'Önceki sohbet';

-- Her kullanıcının aktif oturumu: en son güncellenen thread.
update public.users u
set active_thread_id = t.id
from (
  select distinct on (user_id) user_id, id
  from public.chat_threads
  order by user_id, updated_at desc
) t
where u.id = t.user_id and u.active_thread_id is null;

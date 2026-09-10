-- Plan-içi etkinlikler + plan_agent thread kind (Şahin 2026-09-10)
-- plans.id TEXT FK. RLS açık, anon policy yok (backend service_role).

alter table public.chat_threads
  add column if not exists kind text not null default 'global';

alter table public.chat_threads
  drop constraint if exists chat_threads_kind_check;
alter table public.chat_threads
  add constraint chat_threads_kind_check
  check (kind in ('global', 'plan_agent'));

create unique index if not exists chat_threads_plan_agent_uniq
  on public.chat_threads (user_id, plan_id)
  where kind = 'plan_agent';

create table if not exists public.plan_events (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  plan_id text not null references public.plans(id) on delete cascade,
  title text not null,
  categories text[] not null default '{}',
  scheduled_time text not null default '09:00',
  duration_min int not null default 15,
  recurrence text not null default 'none',
  byweekday int[] not null default '{}',
  start_date date not null,
  end_date date,
  created_by text not null default 'user',
  created_at timestamptz not null default now(),
  constraint plan_events_recurrence_check
    check (recurrence in ('none', 'daily', 'weekdays', 'weekly')),
  constraint plan_events_created_by_check
    check (created_by in ('user', 'agent'))
);

create index if not exists plan_events_user_plan_idx
  on public.plan_events (user_id, plan_id);
create index if not exists plan_events_plan_id_idx
  on public.plan_events (plan_id);

create table if not exists public.plan_event_occurrences (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.plan_events(id) on delete cascade,
  user_id text not null references public.users(id) on delete cascade,
  plan_id text not null references public.plans(id) on delete cascade,
  date date not null,
  status text not null default 'pending',
  completed_at timestamptz,
  constraint plan_event_occurrences_status_check
    check (status in ('pending', 'done')),
  constraint plan_event_occurrences_event_date_uniq unique (event_id, date)
);

create index if not exists plan_event_occurrences_user_date_idx
  on public.plan_event_occurrences (user_id, date);
create index if not exists plan_event_occurrences_event_id_idx
  on public.plan_event_occurrences (event_id);
create index if not exists plan_event_occurrences_plan_id_idx
  on public.plan_event_occurrences (plan_id);

alter table public.plan_events enable row level security;
alter table public.plan_event_occurrences enable row level security;

-- Yaptım logu occurrence_id taşır; 365 tasks FK bunu reddediyordu.
alter table public.point_log drop constraint if exists point_log_task_id_fkey;

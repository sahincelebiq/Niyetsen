-- Niyetsen — Faz 2: çekirdek tablolar (MASTER_PLAN §2)
-- users, streaks, points, plans, tasks. intents/chat_msgs/proofs/fortune_log
-- sonraki yuvalarda (chat kalıcılığı, foto depolama, v2 fal modülü) eklenecek.

create table if not exists public.users (
  id text primary key,
  name text,
  birth_date date,
  zodiac_sign text,
  timezone text not null default 'Europe/Istanbul',
  notif_hour int not null default 8,
  created_at timestamptz not null default now(),
  subscription_status text not null default 'free',
  excuse_count int not null default 0,
  freeze_tokens int not null default 0,
  freeze_last_grant text
);

create table if not exists public.streaks (
  user_id text primary key references public.users(id) on delete cascade,
  current_len int not null default 0,
  best_len int not null default 0,
  last_active_date date,
  silent_miss_streak int not null default 0
);

create table if not exists public.points (
  user_id text not null references public.users(id) on delete cascade,
  category text not null,
  value int not null default 0,
  primary key (user_id, category)
);

create table if not exists public.plans (
  id text primary key,
  user_id text not null unique references public.users(id) on delete cascade,
  duration_days int not null,
  batch_generated_until int not null,
  start_date date not null,
  created_at timestamptz not null default now()
);

create table if not exists public.tasks (
  id text primary key,
  plan_id text not null references public.plans(id) on delete cascade,
  day_no int not null,
  day_theme text not null default '',
  date date,
  title text not null,
  task_type text not null default 'alışkanlık',
  categories text[] not null default '{}',
  image_keyword text not null default '',
  image_url text not null default '',
  duration_min int not null default 15,
  tiny_version text not null default '',
  status text not null default 'pending',
  proof_attempts int not null default 0
);
create index if not exists tasks_plan_id_idx on public.tasks(plan_id);

-- RLS: hiç policy yok = anon/authenticated hiçbir erişim yok. Backend service_role
-- ile bypass eder; tüm yetkilendirme FastAPI JWT middleware'inde (api/routes.py).
alter table public.users enable row level security;
alter table public.streaks enable row level security;
alter table public.points enable row level security;
alter table public.plans enable row level security;
alter table public.tasks enable row level security;

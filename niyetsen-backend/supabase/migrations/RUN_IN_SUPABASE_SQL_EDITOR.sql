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

-- Cron performansı: gün bazlı görev sorguları (ReadTimeout önleme)
create index if not exists tasks_plan_date_idx
  on public.tasks(plan_id, date);

create index if not exists tasks_date_status_idx
  on public.tasks(date, status);

create index if not exists tasks_date_pending_idx
  on public.tasks(date)
  where status = 'pending';

-- ============================================================
-- FAZ 7 (V2): Fal modülü — fortune_log (2026-07-16)
-- ============================================================
create table if not exists public.fortune_log (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  type text not null check (type in ('tarot', 'kahve', 'el', 'burc')),
  day date not null,
  result_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists fortune_log_user_type_day_idx
  on public.fortune_log(user_id, type, day);
alter table public.fortune_log enable row level security;

-- ============================================================
-- FAZ 7 Dalga 2: Günlük Tarot push idempotency (2026-07-17)
-- ============================================================
alter table public.push_tokens
  add column if not exists last_tarot_push_date date;

-- ============================================================
-- FAZ 7.6: Sohbet oturumları — chat_threads (2026-07-17)
-- ============================================================
create table if not exists public.chat_threads (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  plan_id text references public.plans(id) on delete set null,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists chat_threads_user_updated_idx
  on public.chat_threads(user_id, updated_at desc);
alter table public.chat_threads enable row level security;
alter table public.chat_msgs
  add column if not exists thread_id uuid references public.chat_threads(id) on delete cascade;
create index if not exists chat_msgs_thread_idx on public.chat_msgs(thread_id, created_at);
alter table public.users add column if not exists active_thread_id uuid;
insert into public.chat_threads (user_id, plan_id, title, created_at, updated_at)
select m.user_id, m.plan_id, 'Önceki sohbet', min(m.created_at), max(m.created_at)
from public.chat_msgs m where m.thread_id is null group by m.user_id, m.plan_id;
update public.chat_msgs m set thread_id = t.id from public.chat_threads t
where m.thread_id is null and t.user_id = m.user_id
  and (t.plan_id = m.plan_id or (t.plan_id is null and m.plan_id is null))
  and t.title = 'Önceki sohbet';
update public.users u set active_thread_id = t.id
from (select distinct on (user_id) user_id, id from public.chat_threads
      order by user_id, updated_at desc) t
where u.id = t.user_id and u.active_thread_id is null;
-- FAZ 7.7 (Dalga 4.3): İdol Modu persona dosyaları — Supabase depolama.
-- Markdown (knowledge/idoller.md) tohum kalır; ASIL KAYNAK artık DB'dir.
-- Böylece yeni idol eklemek deploy gerektirmez (Şahin panelden/scriptten besler).

create table if not exists public.idol_personas (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,                 -- "greenlights-yolu", "first-principles-yolu"
  path_name text not null,                   -- SUNUM ADI (felsefe): "Greenlights Yolu"
  tagline text not null default '',
  category text not null default 'genel',    -- girisimci|sporcu|bilim|sanat|tarih|genel
  -- Kişi adı YALNIZ kaynak/ilham göstergesi olarak tutulur; arayüzde paket adı
  -- kullanılır, kişi adı "ilham alır" cümlesinde geçer (kişilik hakları + Apple 5.2.1).
  inspired_by text not null default '',
  source_note text not null default '',
  -- Persona dossier (15 alanlı model): why_important, core_beliefs, mindset,
  -- habits, daily_routine, sports_or_physical_practice, reading_profile,
  -- books_read_or_recommended, decision_style, failure_and_recovery,
  -- public_quotes, lessons_for_users, sources ...
  dossier jsonb not null default '{}'::jsonb,
  tags text[] not null default '{}',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idol_personas_active_idx
  on public.idol_personas(is_active, category);

alter table public.idol_personas enable row level security;

-- RAG parçaları: 80-150 kelimelik bloklar, embedding önbelleğiyle birlikte.
-- pgvector kurulu değilse embedding float8[] olarak saklanır (kosinüs kodda).
create table if not exists public.persona_chunks (
  id uuid primary key default gen_random_uuid(),
  persona_id uuid not null references public.idol_personas(id) on delete cascade,
  section text not null,                     -- overview|mindset|habits|books|lessons...
  chunk_index int not null default 0,
  text text not null,
  embedding float8[],                        -- null: keyword fallback kullanılır
  created_at timestamptz not null default now()
);

create index if not exists persona_chunks_persona_idx
  on public.persona_chunks(persona_id, section);

alter table public.persona_chunks enable row level security;

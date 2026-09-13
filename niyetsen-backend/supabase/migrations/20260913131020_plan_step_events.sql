-- Plan etkinlikleri adım evrimi (prod 20260913131020 ile eşitleme, 2026-09-13)
-- Prod'da agent ile uygulanmış; bu dosya fresh DB'lerin aynı son duruma gelmesi içindir.
-- Tamamı idempotent (IF NOT EXISTS).

-- 1) plan_events: görev bağlantısı + not + hatırlatıcı + soft delete
alter table public.plan_events
  add column if not exists task_id text null references public.tasks(id) on delete set null;
alter table public.plan_events
  add column if not exists note text not null default '';
alter table public.plan_events
  add column if not exists remind_offset_min int not null default 0;
alter table public.plan_events
  add column if not exists reminder_priority text not null default 'normal';
alter table public.plan_events
  add column if not exists updated_at timestamptz not null default now();
alter table public.plan_events
  add column if not exists deleted_at timestamptz null;

alter table public.plan_events
  drop constraint if exists plan_events_remind_offset_check;
alter table public.plan_events
  add constraint plan_events_remind_offset_check
  check ((remind_offset_min >= 0) and (remind_offset_min <= 1440));

alter table public.plan_events
  drop constraint if exists plan_events_reminder_priority_check;
alter table public.plan_events
  add constraint plan_events_reminder_priority_check
  check (reminder_priority in ('low', 'normal', 'high'));

alter table public.plan_events
  drop constraint if exists plan_events_note_len_check;
alter table public.plan_events
  add constraint plan_events_note_len_check
  check (char_length(note) <= 2000);

create index if not exists plan_events_task_id_idx
  on public.plan_events (task_id) where (task_id is not null);
create index if not exists plan_events_user_active_idx
  on public.plan_events (user_id, plan_id) where (deleted_at is null);
create unique index if not exists plan_events_task_active_uniq
  on public.plan_events (task_id) where ((task_id is not null) and (deleted_at is null));

-- 2) occurrences: durum genişletme + puan kaynağı (zaman kolonları 131242'de)
alter table public.plan_event_occurrences
  add column if not exists points_source text null;
alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_status_check;
alter table public.plan_event_occurrences
  add constraint plan_event_occurrences_status_check
  check (status in ('pending', 'done', 'skipped', 'missed'));
alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_points_source_check;
alter table public.plan_event_occurrences
  add constraint plan_event_occurrences_points_source_check
  check ((points_source is null) or (points_source in ('self', 'task')));

-- 3) plan_step_notes: görev adım notları (kullanıcı başına görevde tek satır)
create table if not exists public.plan_step_notes (
  user_id text not null references public.users(id) on delete cascade,
  task_id text not null references public.tasks(id) on delete cascade,
  body text not null default '',
  updated_at timestamptz not null default now(),
  constraint plan_step_notes_pkey primary key (user_id, task_id),
  constraint plan_step_notes_body_len_check check (char_length(body) <= 2000)
);
create index if not exists plan_step_notes_task_id_idx
  on public.plan_step_notes (task_id);
alter table public.plan_step_notes enable row level security;
-- RLS: policy yok — deny-by-default, yalnız backend service_role (08 kuralı).

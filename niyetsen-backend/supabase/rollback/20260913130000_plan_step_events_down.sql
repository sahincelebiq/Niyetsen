-- GERİ ALMA — 20260913130000_plan_step_events.sql
-- Yalnız gerekirse SQL Editor'da tek seferde çalıştır. Veri kaybı:
--   • plan_step_notes içeriği silinir.
--   • plan_events.task_id / note / hatırlatma alanları düşer.
--   • skipped/missed olaylar pending'e döner (eski check 2 durumu tanır).
--   • point_log.task_id hiç değişmediği için puan geçmişi ve rapor eski yola döner.

-- 4) plan_step_notes
drop table if exists public.plan_step_notes;

-- 3) point_log
drop index if exists public.point_log_source_idx;
drop index if exists public.point_log_complete_once_uniq;
drop trigger if exists point_log_fill_source_trg on public.point_log;
drop function if exists public.point_log_fill_source();
alter table public.point_log drop constraint if exists point_log_kind_check;
alter table public.point_log drop constraint if exists point_log_source_kind_check;
alter table public.point_log
  drop column if exists kind,
  drop column if exists source_id,
  drop column if exists source_kind;

-- 2) plan_event_occurrences
drop index if exists public.plan_event_occurrences_user_status_date_idx;
drop index if exists public.plan_event_occurrences_remind_due_idx;
alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_points_source_check;
alter table public.plan_event_occurrences
  drop column if exists points_source,
  drop column if exists snoozed_until,
  drop column if exists reminded_at,
  drop column if exists remind_at,
  drop column if exists scheduled_at;
update public.plan_event_occurrences
  set status = 'pending' where status in ('skipped', 'missed');
alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_status_check;
alter table public.plan_event_occurrences
  add constraint plan_event_occurrences_status_check
  check (status in ('pending', 'done'));

-- 1) plan_events
drop index if exists public.plan_events_user_active_idx;
drop index if exists public.plan_events_task_id_idx;
drop index if exists public.plan_events_task_active_uniq;
alter table public.plan_events drop constraint if exists plan_events_note_len_check;
alter table public.plan_events drop constraint if exists plan_events_remind_offset_check;
alter table public.plan_events drop constraint if exists plan_events_reminder_priority_check;
alter table public.plan_events
  drop column if exists deleted_at,
  drop column if exists updated_at,
  drop column if exists reminder_priority,
  drop column if exists remind_offset_min,
  drop column if exists note,
  drop column if exists task_id;

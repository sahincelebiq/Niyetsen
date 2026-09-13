-- 2026-09-13 — 04 Plan → Etkinlik → Bildirim → Puan hattı (Şahin onayı: Q1–Q12 varsayılan)
--
-- Kavram eşlemesi (yeni tablo yalnız notlar için):
--   plan_adimi = public.tasks               (değişmez plan içeriği — kolon eklenmez)
--   etkinlik   = public.plan_events         (kural: saat, tekrar, süre) + adım bağı
--   olay       = public.plan_event_occurrences (belirli günün somut örneği)
--
-- Kararlar:
--   • Serbest etkinlik = plana bağlı, adımsız (task_id NULL). plan_id NOT NULL kalır.
--   • Adım başına tek AKTİF etkinlik (partial unique).
--   • Silme = soft delete (deleted_at); tamamlanmış olaylar ve puan geçmişi KALIR.
--   • Olay: date+scheduled_time yerel kural, scheduled_at UTC anı (depolama UTC, hesap yerel).
--   • remind_at = etkin hatırlatma anı (offset/ertelemeyi içerir) → cron tek indeksle tarar.
--   • Puan idempotency: point_log (source_kind, source_id, category) WHERE kind='complete' UNIQUE.
--     Uygulama katmanındaki koşullu UPDATE birinci kilit, bu indeks son söz.
--   • point_log yeni kolonları NULL gelirse trigger reason'dan türetir → deploy edilmiş backend
--     değişmeden korumaya girer; backend güncellenince alanları kendisi yazar.
--   • RLS açık, policy YOK (backend service_role) — docs/supabase/SCHEMA_DURUM.md.
--
-- Geri alma: 20260913130000_plan_step_events_down.sql

-- ============================================================
-- 1) plan_events — adım bağı + not + hatırlatma + soft silme
-- ============================================================
alter table public.plan_events
  add column if not exists task_id text references public.tasks(id) on delete set null,
  add column if not exists note text not null default '',
  add column if not exists remind_offset_min int not null default 0,
  add column if not exists reminder_priority text not null default 'normal',
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists deleted_at timestamptz;

alter table public.plan_events
  drop constraint if exists plan_events_reminder_priority_check;
alter table public.plan_events
  add constraint plan_events_reminder_priority_check
  check (reminder_priority in ('low', 'normal', 'high'));

alter table public.plan_events
  drop constraint if exists plan_events_remind_offset_check;
alter table public.plan_events
  add constraint plan_events_remind_offset_check
  check (remind_offset_min between 0 and 1440);

alter table public.plan_events
  drop constraint if exists plan_events_note_len_check;
alter table public.plan_events
  add constraint plan_events_note_len_check
  check (char_length(note) <= 2000);

-- Adım başına tek aktif etkinlik (soft-silinmişler sayılmaz).
create unique index if not exists plan_events_task_active_uniq
  on public.plan_events (task_id)
  where task_id is not null and deleted_at is null;

-- FK covering index (on delete set null aramaları).
create index if not exists plan_events_task_id_idx
  on public.plan_events (task_id)
  where task_id is not null;

-- Aktif etkinlik listeleri (materializasyon + Planım).
create index if not exists plan_events_user_active_idx
  on public.plan_events (user_id, plan_id)
  where deleted_at is null;

-- ============================================================
-- 2) plan_event_occurrences — durum genişlemesi + UTC anı + bildirim
-- ============================================================
alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_status_check;
alter table public.plan_event_occurrences
  add constraint plan_event_occurrences_status_check
  check (status in ('pending', 'done', 'skipped', 'missed'));

alter table public.plan_event_occurrences
  add column if not exists scheduled_at timestamptz,   -- date + scheduled_time @ users.timezone → UTC
  add column if not exists remind_at timestamptz,      -- scheduled_at - remind_offset; erteleme burayı ileri alır
  add column if not exists reminded_at timestamptz,    -- sunucu push gönderildi (idempotent)
  add column if not exists snoozed_until timestamptz,  -- "15 dk ertele" rozeti için
  add column if not exists points_source text;         -- 'self' (Yaptım +50) | 'task' (gölge; puan görevden)

alter table public.plan_event_occurrences
  drop constraint if exists plan_event_occurrences_points_source_check;
alter table public.plan_event_occurrences
  add constraint plan_event_occurrences_points_source_check
  check (points_source is null or points_source in ('self', 'task'));

-- Cron: vadesi gelen, henüz hatırlatılmamış bekleyen olaylar.
create index if not exists plan_event_occurrences_remind_due_idx
  on public.plan_event_occurrences (remind_at)
  where status = 'pending' and reminded_at is null;

-- Bugün / rapor: kullanıcı + durum + gün.
create index if not exists plan_event_occurrences_user_status_date_idx
  on public.plan_event_occurrences (user_id, status, date);

-- Backfill: mevcut olaylara UTC anı. Geçersiz timezone adı → Europe/Istanbul.
update public.plan_event_occurrences o
set
  scheduled_at = (o.date + e.scheduled_time::time)
                   at time zone coalesce(tz.name, 'Europe/Istanbul'),
  remind_at    = ((o.date + e.scheduled_time::time)
                   at time zone coalesce(tz.name, 'Europe/Istanbul'))
                 - make_interval(mins => e.remind_offset_min),
  points_source = case when o.status = 'done' then 'self' else o.points_source end
from public.plan_events e
join public.users u on u.id = e.user_id
left join pg_timezone_names tz on tz.name = u.timezone
where o.event_id = e.id
  and o.scheduled_at is null;

-- ============================================================
-- 3) point_log — kaynak tipi + tür + DB seviyesinde idempotent tamamlama
-- ============================================================
alter table public.point_log
  add column if not exists source_kind text,
  add column if not exists source_id text,
  add column if not exists kind text;

alter table public.point_log
  drop constraint if exists point_log_source_kind_check;
alter table public.point_log
  add constraint point_log_source_kind_check
  check (source_kind is null or source_kind in ('task', 'occurrence', 'bonus', 'system'));

alter table public.point_log
  drop constraint if exists point_log_kind_check;
alter table public.point_log
  add constraint point_log_kind_check
  check (kind is null or kind in ('complete', 'penalty', 'excuse', 'bonus', 'halving'));

-- Türetme: reason metni scoring_service.py'nin yazdığı sabitlerdir.
create or replace function public.point_log_fill_source()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.kind is null then
    new.kind := case
      when new.reason in ('görev tamamlandı', 'etkinlik tamamlandı') then 'complete'
      when new.reason like 'sessiz kaçırma%' then 'penalty'
      when new.reason like 'mazeretli%' then 'excuse'
      when new.reason like 'motivasyon bonus%' then 'bonus'
      when new.reason like '10 mazeret%' then 'halving'
      else null
    end;
  end if;
  if new.source_kind is null then
    new.source_kind := case
      when new.reason like 'motivasyon bonus%' then 'bonus'
      when new.task_id is null then 'system'
      when new.reason = 'etkinlik tamamlandı' then 'occurrence'
      else 'task'
    end;
  end if;
  if new.source_id is null then
    new.source_id := case
      when new.task_id is not null then new.task_id
      when new.reason like 'motivasyon bonus görevi:%' then split_part(new.reason, ':', 2)
      else null
    end;
  end if;
  return new;
end;
$$;

revoke all on function public.point_log_fill_source() from public, anon, authenticated;

drop trigger if exists point_log_fill_source_trg on public.point_log;
create trigger point_log_fill_source_trg
  before insert on public.point_log
  for each row execute function public.point_log_fill_source();

-- Backfill: mevcut 129 satır (trigger INSERT'te çalışır; eskiler için aynı eşleme).
update public.point_log p
set
  kind = case
    when p.reason in ('görev tamamlandı', 'etkinlik tamamlandı') then 'complete'
    when p.reason like 'sessiz kaçırma%' then 'penalty'
    when p.reason like 'mazeretli%' then 'excuse'
    when p.reason like 'motivasyon bonus%' then 'bonus'
    when p.reason like '10 mazeret%' then 'halving'
    else null
  end,
  source_kind = case
    when p.reason like 'motivasyon bonus%' then 'bonus'
    when p.task_id is null then 'system'
    when p.reason = 'etkinlik tamamlandı'
      or exists (select 1 from public.plan_event_occurrences o where o.id::text = p.task_id)
      then 'occurrence'
    else 'task'
  end,
  source_id = case
    when p.task_id is not null then p.task_id
    when p.reason like 'motivasyon bonus görevi:%' then split_part(p.reason, ':', 2)
    else null
  end
where p.kind is null or p.source_kind is null;

-- Aynı kaynak (görev / olay) aynı kategoriye iki kez 'complete' yazamaz.
-- Backfill SONRASI kurulur; çift kayıt varsa migration burada bilinçli olarak durur.
create unique index if not exists point_log_complete_once_uniq
  on public.point_log (source_kind, source_id, category)
  where kind = 'complete';

create index if not exists point_log_source_idx
  on public.point_log (source_kind, source_id);

-- ============================================================
-- 4) plan_step_notes — adım notu (kullanıcı metni; tasks'i kirletmez)
-- ============================================================
create table if not exists public.plan_step_notes (
  user_id text not null references public.users(id) on delete cascade,
  task_id text not null references public.tasks(id) on delete cascade,
  body text not null default '',
  updated_at timestamptz not null default now(),
  primary key (user_id, task_id),
  constraint plan_step_notes_body_len_check check (char_length(body) <= 2000)
);

create index if not exists plan_step_notes_task_id_idx
  on public.plan_step_notes (task_id);

alter table public.plan_step_notes enable row level security;
-- Policy yok = deny-by-default; istemci PostgREST ile okumaz (default privileges 2026-08-20'de kapatıldı).
revoke all on table public.plan_step_notes from anon, authenticated;

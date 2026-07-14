-- Cron performansı: gün bazlı görev sorguları için indeksler
-- Supabase SQL Editor başlığı: Niyetsen — Cron görev indeksleri

create index if not exists tasks_plan_date_idx
  on public.tasks(plan_id, date);

create index if not exists tasks_date_status_idx
  on public.tasks(date, status);

create index if not exists tasks_date_pending_idx
  on public.tasks(date)
  where status = 'pending';

-- FAZ 7 (V2): Fal modülü — fortune_log (MASTER_PLAN §2'deki v2 tablosu).
-- Hak sayaçları günlük sıfırlanır; sayım (user_id, type, day) indeksiyle ucuz.

create table if not exists public.fortune_log (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  type text not null check (type in ('tarot', 'kahve', 'el', 'burc')),
  day date not null,
  result_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Günlük hak sayacı sorgusu: count(*) where user+type+day.
create index if not exists fortune_log_user_type_day_idx
  on public.fortune_log(user_id, type, day);

-- Diğer tablolarla tutarlı: RLS açık, erişim yalnız service_role (backend).
alter table public.fortune_log enable row level security;

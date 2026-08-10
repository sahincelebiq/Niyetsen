-- faz8.13/4 — Online rekabet: opt-in takma adlı gelişim ligi
-- (Şahin kararı 2026-08-10: leaderboard öne çekildi).
-- KVKK: yalnız kullanıcının seçtiği RUMUZ + puan + zincir tutulur;
-- gerçek isim/e-posta bu tabloya ASLA yazılmaz. Opt-out = satır silinir.
-- Erişim: deny-by-default (policy yok) — yalnız backend service_role.

create table if not exists public.league_members (
  user_id uuid primary key references auth.users (id) on delete cascade,
  alias text not null check (char_length(alias) between 2 and 24),
  score integer not null default 0 check (score >= 0),
  streak integer not null default 0 check (streak >= 0),
  updated_at timestamptz not null default now()
);

create index if not exists league_members_score_idx
  on public.league_members (score desc, streak desc);

alter table public.league_members enable row level security;

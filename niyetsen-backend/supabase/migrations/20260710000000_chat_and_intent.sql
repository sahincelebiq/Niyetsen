-- Niyetsen — Faz 2: sohbet geçmişi + niyet kalıcılığı (MASTER_PLAN §2)
-- Şu ana kadar sohbet mesajları ve toplanan niyet sadece mobil local state'te
-- yaşıyordu (uygulama kapanınca/silinince kaybolur, plan kaybolmaz). Bu migration
-- chat_msgs + intents tablolarını ekler; plans zaten var, intent_id opsiyonel bağ.

create table if not exists public.intents (
  id text primary key,
  user_id text not null references public.users(id) on delete cascade,
  text text not null default '',
  duration_days int not null default 365,
  status text not null default 'active', -- active | done | abandoned
  created_at timestamptz not null default now()
);
create index if not exists intents_user_id_idx on public.intents(user_id);

create table if not exists public.chat_msgs (
  id bigint generated always as identity primary key,
  user_id text not null references public.users(id) on delete cascade,
  role text not null, -- 'user' | 'assistant'
  content text not null,
  created_at timestamptz not null default now()
);
create index if not exists chat_msgs_user_id_created_idx on public.chat_msgs(user_id, created_at);

-- RLS: hiç policy yok = anon/authenticated hiçbir erişim yok (mevcut tablolarla
-- aynı desen). Backend service_role ile bypass eder; yetkilendirme FastAPI
-- JWT middleware'inde (api/routes.py > get_current_user).
alter table public.intents enable row level security;
alter table public.chat_msgs enable row level security;

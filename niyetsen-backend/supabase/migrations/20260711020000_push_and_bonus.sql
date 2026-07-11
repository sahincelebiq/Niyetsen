-- FAZ 4: push token registry and idempotent bonus-task offers.

create table if not exists public.push_tokens (
  id bigint generated always as identity primary key,
  user_id text not null references public.users(id) on delete cascade,
  token text not null unique,
  platform text not null check (platform in ('ios', 'android')),
  enabled boolean not null default true,
  last_task_reminder_date date,
  last_bonus_offer_date date,
  updated_at timestamptz not null default now()
);
create index if not exists push_tokens_user_idx on public.push_tokens(user_id);
alter table public.push_tokens enable row level security;

create table if not exists public.bonus_offers (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  bonus_key text not null,
  title text not null,
  tiny_instruction text not null,
  category text not null,
  day date not null,
  status text not null default 'offered'
    check (status in ('offered', 'completed', 'expired')),
  completion_id text,
  offered_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (user_id, day)
);
create unique index if not exists bonus_offers_user_completion_uidx
  on public.bonus_offers(user_id, completion_id)
  where completion_id is not null;
create index if not exists bonus_offers_user_status_idx
  on public.bonus_offers(user_id, status, day desc);
alter table public.bonus_offers enable row level security;

create or replace function public.complete_bonus_offer(
  p_user_id text, p_offer_id uuid, p_completion_id text
) returns boolean language plpgsql security definer set search_path = public as $$
declare
  v_changed int;
  v_category text;
begin
  if exists (
    select 1 from public.bonus_offers
    where user_id = p_user_id and completion_id = p_completion_id
  ) then
    return false;
  end if;
  update public.bonus_offers
  set status = 'completed', completion_id = p_completion_id, completed_at = now()
  where id = p_offer_id and user_id = p_user_id and status = 'offered';
  get diagnostics v_changed = row_count;
  if v_changed <> 1 then
    return false;
  end if;
  select category into v_category
  from public.bonus_offers where id = p_offer_id;
  insert into public.points (user_id, category, value)
  values (p_user_id, v_category, 10)
  on conflict (user_id, category)
  do update set value = public.points.value + 10;
  insert into public.point_log (user_id, task_id, category, delta, reason)
  values (
    p_user_id, null, v_category, 10,
    'motivasyon bonus görevi:' || p_offer_id::text
  );
  return true;
end;
$$;

revoke all on function public.complete_bonus_offer(text, uuid, text)
  from public, anon, authenticated;
grant execute on function public.complete_bonus_offer(text, uuid, text)
  to service_role;

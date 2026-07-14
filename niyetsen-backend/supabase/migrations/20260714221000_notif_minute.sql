alter table public.users
  add column if not exists notif_minute int not null default 0;

alter table public.users
  add constraint users_notif_minute_range
  check (notif_minute >= 0 and notif_minute <= 59);

-- FAZ 5: deneme süresi ve abonelik takibi (MASTER_PLAN §1.1, §1.7)

alter table public.users
  add column if not exists trial_started_at timestamptz;

comment on column public.users.subscription_status is
  'free | trial | active | expired | cancelled';
comment on column public.users.trial_started_at is
  'İlk plan üretildiğinde set edilir; 3 günlük deneme başlangıcı.';

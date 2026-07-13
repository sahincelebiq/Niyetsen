-- Abonelik dönem sonu (RevenueCat CANCELLATION sonrası erişim süresi)
alter table public.users
  add column if not exists subscription_expires_at timestamptz;

comment on column public.users.subscription_expires_at is
  'RevenueCat expiration_at_ms — iptal sonrası dönem sonuna kadar erişim.';

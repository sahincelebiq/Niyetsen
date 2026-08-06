-- Play Store çok dilli çıkış: kullanıcı dil tercihi (UI + AI yanıt dili).
-- Değerler: tr | en-US | en-GB | de | fr | ar
alter table public.users
  add column if not exists preferred_language text;

comment on column public.users.preferred_language is
  'App UI + AI reply locale: tr | en-US | en-GB | de | fr | ar';

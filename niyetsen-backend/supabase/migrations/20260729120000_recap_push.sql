-- FAZ 8.8: Niyetsen Raporu push idempotency (14. gün + her 30 günde).

alter table public.push_tokens
  add column if not exists last_recap_push_date date;

-- FAZ 7 Dalga 2: Günlük Tarot push idempotency (görev hatırlatıcısıyla aynı desen).

alter table public.push_tokens
  add column if not exists last_tarot_push_date date;

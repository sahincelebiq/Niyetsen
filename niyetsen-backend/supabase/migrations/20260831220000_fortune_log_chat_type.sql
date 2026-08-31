-- Mistik rehber sohbeti fortune_log'da sayılır (ücretsiz 5, PRO sınırsız).
alter table public.fortune_log drop constraint if exists fortune_log_type_check;
alter table public.fortune_log
  add constraint fortune_log_type_check
  check (type in ('tarot', 'kahve', 'el', 'burc', 'chat'));

-- Niyetsen — Unsplash kalite ve attribution alanları.

alter table public.tasks
  add column if not exists image_source text not null default 'placeholder',
  add column if not exists image_attribution text not null default '',
  add column if not exists image_attribution_url text not null default '';

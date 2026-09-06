-- faz8 — Lig KVKK dilimi: rumuz + hazır avatar + bölge etiketi
-- Mevcut public.league_members üzerine inşa (leagues / league_participants YOK).
-- KVKK: gerçek isim, e-posta, fotoğraf, GPS yazılmaz.
-- score kolonu = tamamlanan görev sayısı anlık görüntüsü (ceza/puan değil).
-- Erişim: deny-by-default + backend service_role (policy ekleme).

alter table public.league_members
  add column if not exists avatar text,
  add column if not exists region text;

alter table public.league_members
  drop constraint if exists league_members_avatar_len;
alter table public.league_members
  add constraint league_members_avatar_len
  check (avatar is null or char_length(avatar) between 2 and 24);

alter table public.league_members
  drop constraint if exists league_members_region_len;
alter table public.league_members
  add constraint league_members_region_len
  check (region is null or char_length(region) between 2 and 40);

create index if not exists league_members_region_score_idx
  on public.league_members (region, score desc, streak desc);

comment on column public.league_members.score is
  'Tamamlanan görev sayısı anlık görüntüsü (sıralama birincil anahtarı). Puan/ceza değil.';
comment on column public.league_members.avatar is
  'Hazır simge anahtarı (allowlist). Fotoğraf URL / gerçek yüz yok.';
comment on column public.league_members.region is
  'Serbest metin etiket (örn. İstanbul). Konum izni / GPS yok.';

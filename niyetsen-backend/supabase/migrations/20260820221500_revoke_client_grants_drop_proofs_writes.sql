-- 2026-08-20: PostgREST savunması (SQL Editor paket I) + kanıt Storage yazma kapatma.
-- Mimari: istemci tablolara gitmez; FastAPI service_role kullanır.
-- proofs bucket yazması yalnız backend (H-06). SELECT own-folder durur.

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
alter default privileges in schema public
  revoke all on tables from anon, authenticated;
alter default privileges in schema public
  revoke all on sequences from anon, authenticated;

drop policy if exists proofs_insert_own on storage.objects;
drop policy if exists proofs_update_own on storage.objects;
drop policy if exists proofs_delete_own on storage.objects;

-- H-06 (2026-09-06): proofs bucket authenticated WRITE kapat.
--
-- Prod (ktweahgrrppmxpdhohdh) doğrulandı: storage.objects üzerinde yalnız
-- proofs_select_own (SELECT, own folder) var. Insert/update/delete YOK.
--
-- Faz 3 (`20260711000000_faz3_task_loop.sql`) hâlâ write policy oluşturur.
-- Taze ortam / o dosyanın yeniden apply'ı yazma yüzeyini geri getirir.
-- Bu migration o policy'leri idempotent drop eder; SELECT own bilinçli kalır
-- (hesap silme / okuma için zararsız). Yazma yalnız FastAPI service_role
-- (POST /task/{id}/proof). Mobil doğrudan Storage upload kullanmaz.
--
-- Saldırı PoC yok — yalnız savunma. Tekrar çalıştırmak güvenli.

drop policy if exists "proofs_insert_own" on storage.objects;
drop policy if exists proofs_insert_own on storage.objects;

drop policy if exists "proofs_update_own" on storage.objects;
drop policy if exists proofs_update_own on storage.objects;

drop policy if exists "proofs_delete_own" on storage.objects;
drop policy if exists proofs_delete_own on storage.objects;

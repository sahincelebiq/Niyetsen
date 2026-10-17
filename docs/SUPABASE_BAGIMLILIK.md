# Supabase Bağımlılık Envanteri (V2 Faz 0 — 2026-10-17)

Niyetsen yakında Supabase'den büyük bir sunucuya taşınacak. İki aday hedef var:
**A)** self-host Supabase (Postgres + GoTrue + PostgREST + Storage aynı kalır,
yalnız alan adı/anahtarlar değişir) ve **B)** standart Postgres + S3-uyumlu depo
(MinIO) + ayrı kimlik sağlayıcı (Keycloak veya kendi auth). Bu belge, kaynak
kodun (`niyetsen-backend/`, `niyetsen-backend/supabase/migrations/`, `mobile/`)
Supabase'e **özel** olarak nereye dokunduğunu dosya:satır düzeyinde listeler ve
her madde için "taşınmada neyi neyle değiştireceğiz" cevabını verir. Yalnız kodda
görülen yazıldı; emin olunmayan yere "(doğrulanmalı)" eklendi.

Temel mimari gerçek (tüm tabloları etkiler): **backend Postgres'e hiç doğrudan
bağlanmıyor.** Tüm veri erişimi `supabase-py` → PostgREST üzerinden; `psycopg`,
`asyncpg`, `sqlalchemy` veya `DATABASE_URL` kullanımı kodda yok
(`rg "DATABASE_URL|psycopg|asyncpg|sqlalchemy" app scripts requirements.txt` → 0).
B yolunda bu yüzden en büyük iş yeni bir `Repository` implementasyonudur;
`app/storage/base.py` arayüzü ve `InMemoryRepository` (`app/storage/repository.py`)
zaten soyutlama sınırını çiziyor.

Zorluk sütunu **B yolu** için verilmiştir; A yolunda çoğu madde "değişmez"dir.

---

## 1. Python SDK ve PostgREST'e özel çağrılar (DB/SDK)

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 1 | `supabase>=2.9` paketi (postgrest, storage3, supabase_auth taşır) | `niyetsen-backend/requirements.txt:10` | SDK | A: değişmez. B: paket kaldırılır; `psycopg[binary,pool]` (veya SQLAlchemy Core) + `boto3`/`minio` + Keycloak admin istemcisi eklenir. | yüksek |
| 2 | `create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, ClientOptions(postgrest_client_timeout, storage_client_timeout))` — service_role ile RLS bypass | `app/storage/supabase_repository.py:16`, `:146-153` | SDK | A: URL/anahtar değişir. B: `psycopg_pool.ConnectionPool(DATABASE_URL)`; timeout `statement_timeout`/`connect_timeout` ile. | orta |
| 3 | PostgREST sorgu kurucu `.table(...).select/insert/update/delete/eq/in_/order/limit` — 120 çağrı; tüm veri katmanı | `app/storage/supabase_repository.py` (ör. `:162-272`, `:456-531`, `:1563-1644`) | DB | A: değişmez. B: `PostgresRepository` yazılır; her metot parametreli SQL'e çevrilir. `Repository` arayüzü (`app/storage/base.py`) ve testlerin kullandığı `InMemoryRepository` korunur. | yüksek |
| 4 | `.upsert(..., on_conflict=...)` — 14 upsert / 10 açık `on_conflict` (plans `id`, tasks `id`, plan_step_notes `user_id,task_id`, chat_msgs `user_id,client_message_id`, user_consents `user_id,consent_kind,version`, push_tokens `token`, bonus_offers `user_id,day`, idol_personas `slug`, league_members `user_id`) | `supabase_repository.py:197`, `:205`, `:259-267`, `:272`, `:490-497`, `:801`, `:1054-1060`, `:1064-1070`, `:1164-1174`, `:1348`, `:1382-1388`, `:1419`, `:1498`, `:1610-1612` | DB | A: değişmez. B: `INSERT … ON CONFLICT (…) DO UPDATE SET …` — çakışma anahtarları birebir taşınır (unique index'ler migration'larda mevcut). | orta |
| 5 | `select("id", count="exact")` — sayım PostgREST `Prefer: count=exact` başlığıyla | `supabase_repository.py:353`, `:441`, `:918`, `:1290`, `:1298`, `:1409` | DB | A: değişmez. B: `SELECT count(*)` veya `EXISTS(...)`; `:918` (`delete(count="exact")`) için `DELETE … RETURNING`/rowcount. | düşük |
| 6 | Gömülü kaynak (embedded resource) `!inner` — PostgREST'e özgü JOIN sözdizimi: `tasks.select("*, plans!inner(user_id)")` (sahiplik doğrulaması) ve `push_tokens … users!inner(timezone,notif_hour,notif_minute)` | `supabase_repository.py:456`, `:1087` | DB | A: değişmez. B: açık `JOIN plans p ON p.id = t.plan_id WHERE p.user_id = %s` / `JOIN users u ON u.id = pt.user_id`. | düşük |
| 7 | `.range(a, b)` sayfalama (PostgREST `Range` başlığı) — plan günleri ve push token taraması | `supabase_repository.py:702`, `:1090` | DB | A: değişmez. B: `LIMIT/OFFSET` veya keyset (`WHERE token > %s ORDER BY token`). | düşük |
| 8 | postgrest-py `maybe_single()`/`single()` davranışı (sıfır satırda `None`; `_maybe_single` sarmalayıcı 31 kullanım) | `supabase_repository.py:33-37`, `:1009`, `:1201` | SDK | A: değişmez. B: `cursor.fetchone()`; sarmalayıcı sadeleşir. | düşük |
| 9 | Unique ihlali tespiti `exc.code == "23505"` (PostgREST `APIError.code`) + metin eşleşmesi | `app/storage/db_coerce.py:8-19` | SDK | A: değişmez. B: `psycopg.errors.UniqueViolation` yakalanır; metin fallback kalabilir. | düşük |
| 10 | jsonb'nin PostgREST'ten bazen dict bazen JSON-string gelmesi (çift encode) | `app/storage/db_coerce.py:22-42` | SDK | A: değişmez. B: psycopg jsonb'yi doğrudan dict döner; fonksiyon zararsız kalır (silinebilir). | düşük |
| 11 | Depo seçimi `USE_SUPABASE_DB` → `SupabaseRepository` geç import; prod kilidi "USE_SUPABASE_DB=true olmalı" | `app/storage/repository.py:938-944`, `app/main.py:30-34`, `app/config.py:90` | SDK | A: değişmez. B: bayrak `DB_BACKEND=postgres|memory` (veya `DATABASE_URL` doluysa) olur; kilit mesajı güncellenir. | düşük |
| 12 | `_same_user_id` — "PostgREST uuid vs JWT text" büyük/küçük harf farkını yutma (league_members.user_id uuid, users.id text) | `app/services/league_service.py:60-66` | DB | A: değişmez. B: `league_members.user_id` text'e çevrilince (bkz. #25) gereksizleşir. | düşük |
| 13 | `persona_service` DB/dosya fallback kararı `USE_SUPABASE_DB` üzerinden | `app/services/persona_service.py:5-8`, `:123` | SDK | A: değişmez. B: #11 ile aynı bayrak adı. | düşük |

Not: `.rpc(` çağrıları ve Storage çağrıları aşağıda ayrı tablolarda. `app_metadata`
yazımı, `auth.admin.get_user_by_id`, `auth.admin.update_user_by_id`, `postgrest`
doğrudan import'u ve `create_signed_url` **kodda yok** (rg 0 sonuç).

---

## 2. RPC fonksiyonları (security definer) ve rol grant'leri

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 14 | `claim_proof_attempt(p_user_id, p_task_id, p_idempotency_key)` — `FOR UPDATE` + 2 dk stale reclaim; `rows[0]` ile tablo dönüşü okunur | çağrı `supabase_repository.py:590-608`; tanım `supabase/migrations/20260711010000_consent_and_proof_guards.sql:41-100`, güncel gövde `20260714220000_proof_stale_reclaim.sql:3-60` | RPC | A: değişmez. B: Fonksiyon standart plpgsql — aynen taşınır; `security definer` + `grant … to service_role` yerine uygulama rolüne `EXECUTE`. Çağrı `SELECT * FROM public.claim_proof_attempt(%s,%s,%s)`. Alternatif: mantığı Python tarafında tek transaction'a alma (önerilmez; atomiklik kaybı). | orta |
| 15 | `finish_proof_attempt(p_user_id, p_task_id, p_idempotency_key, p_result jsonb)` | çağrı `supabase_repository.py:617-622`; tanım `20260711010000_consent_and_proof_guards.sql:102-123` | RPC | A: değişmez. B: `SELECT public.finish_proof_attempt(%s,%s,%s,%s::jsonb)`; `RAISE EXCEPTION` → psycopg `RaiseException` eşlemesi. | orta |
| 16 | `abort_proof_attempt(...)` (language sql) | çağrı `supabase_repository.py:627-631`; tanım `…consent_and_proof_guards.sql:125-131` | RPC | A: değişmez. B: aynen taşınır. | düşük |
| 17 | `complete_bonus_offer(p_user_id, p_offer_id uuid, p_completion_id)` — idempotent tamamlama + `points` upsert + `point_log` insert | çağrı `supabase_repository.py:1182-1187`; tanım `20260711020000_push_and_bonus.sql:38-71` | RPC | A: değişmez. B: aynen taşınır; dönüş `boolean`. | orta |
| 18 | `revoke all on function … from public, anon, authenticated; grant execute … to service_role` | `20260711010000_consent_and_proof_guards.sql:133-141`, `20260711020000_push_and_bonus.sql:73-76` | Policy | A: değişmez. B: `anon`/`authenticated`/`service_role` rolleri yok → `grant execute … to niyetsen_app`. Migration'lar koşullu (`DO $$ IF EXISTS role`) yazılmalı. | düşük |

---

## 3. Auth / JWT doğrulama (backend)

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 19 | JWKS adresi **sabit türetiliyor**: `PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")`; ayrı `SUPABASE_JWKS_URL` env'i YOK (rg 0) | `app/api/routes.py:175-185`; `.env.example:43-44` (yorum) | Auth | A: `SUPABASE_URL` değişince otomatik. B: `AUTH_JWKS_URL` env (Keycloak: `https://…/realms/<realm>/protocol/openid-connect/certs`); PyJWKClient aynen kalır. | düşük |
| 20 | `jwt.decode(..., algorithms=["RS256","ES256"], audience="authenticated")` — Supabase'in sabit `aud` claim'i | `app/api/routes.py:202-208` | Auth | A: değişmez. B: Keycloak'ta `aud` client-id/`account`; `AUTH_AUDIENCE` + `AUTH_ISSUER` env'den okunur, `issuer=` doğrulaması eklenir. | orta |
| 21 | Kullanılan claim'ler: `sub` → `user_id` (DB'de `users.id text` = Supabase auth UUID), `email` → dev allowlist (`register_if_dev`). `role`/`aud` claim'i başka yerde kullanılmıyor | `app/api/routes.py:213-220`, `app/core/dev_accounts.py:30` | Auth | A: `auth.users` dışa/içe aktarılırsa `sub` korunur → değişmez. B: Keycloak `sub` **farklı bir UUID** üretir → tüm `users.id` FK zinciri kopar. Çözüm: kullanıcı içe aktarırken Keycloak'ta `id` alanını Supabase UUID'siyle set etmek (Admin API create-user `id` alanı — doğrulanmalı) **veya** `users.auth_subject` eşleme kolonu + login'de çeviri. `email` claim'i Keycloak'ta `email` scope ile gelir. | yüksek |
| 22 | Hesap silme: `self._db.auth.admin.delete_user(user_id)` (GoTrue admin) — `DELETE /me` | `app/storage/supabase_repository.py:1265-1271`; uç `app/api/routes.py:1797-1803` | Auth | A: değişmez. B: Keycloak Admin REST `DELETE /admin/realms/{realm}/users/{id}` (service account token) — `AuthGateway.delete_user()`; başarısızlıkta mevcut `RuntimeError` davranışı korunur. | orta |
| 23 | Rate limiter imzasız `sub` okuması (herhangi bir JWT ile çalışır) | `app/core/rate_limit.py:18-20` | Auth | A/B: değişmez (not için listelendi). | düşük |
| 24 | `SUPABASE_JWT_SECRET` yalnız env düzenleme script'inin yazdığı **placeholder**; uygulama okumuyor (HS256 legacy kaldırılmış) | `niyetsen-backend/scripts/organize_env.py:136-137` | Auth | A/B: satır silinir. | düşük |

---

## 4. Migration'larda Supabase'e özel SQL

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 25 | **Tek `auth.users` FK**: `league_members.user_id uuid primary key references auth.users(id) on delete cascade` — diğer tüm tablolar `public.users(id)` (text) referans alır | `supabase/migrations/20260810120000_faz813_league_members.sql:8` | DB/Auth | A: çalışır ama `users.id text` ile tip uyumsuzluğu (#12) sürer. B: `auth` şeması yok → `user_id text primary key references public.users(id) on delete cascade` olarak yeniden yazılır; veri `::text` ile taşınır. | orta |
| 26 | Storage RLS policy'leri `auth.uid()::text` + `storage.foldername(name)[1]` ile "kendi klasörü" — yalnız `proofs_select_own` yürürlükte; insert/update/delete 2026-08-20'de drop edildi | `20260711000000_faz3_task_loop.sql:47-85`; drop `20260820221500_revoke_client_grants_drop_proofs_writes.sql:12-14` | Policy | A: değişmez. B: `storage.objects`/`auth.uid()` yok. İstemci Storage'a zaten erişmiyor (bkz. §6) → MinIO bucket policy "private, yalnız backend erişim anahtarı" yeterli; `proofs_select_own` karşılığı gerekmez. | düşük |
| 27 | `insert into storage.buckets` → `proofs` (private, `file_size_limit` 5 MB, `allowed_mime_types` jpeg/png) | `20260711000000_faz3_task_loop.sql:34-45` | Storage | A: değişmez. B: `mc mb minio/proofs` + private policy; boyut/MIME sınırı uygulama tarafında zaten var (`PROOF_MAX_BYTES`, mime kontrolü) — sunucu tarafı sınır MinIO'da yoktur (bilinçli kabul). | düşük |
| 28 | `insert into storage.buckets` → `plan-images` (public, 5 MB, jpeg/png/webp) | `20260716000000_plan_images_bucket.sql:2-10` | Storage | A: değişmez. B: `plan-images` bucket + anonim `GetObject` policy (listing kapalı). | düşük |
| 29 | `plan_images_public_read` SELECT policy (sonra listing yüzeyi için drop edildi; object URL çalışmaya devam) | create `20260716000000_plan_images_bucket.sql:13-17`; drop `20260802160000_faz8_schema_normalize_indexes_storage.sql:27` | Policy | A: değişmez. B: MinIO'da "download-only" anonim policy = aynı etki. | düşük |
| 30 | **Tüm tablolarda RLS açık, policy yok** (deny-by-default; backend service_role ile bypass eder) | `20260707000000_niyetsen_core_tables.sql:63-67`, `20260710000000_chat_and_intent.sql:28-29`, `20260711010000…:14,39`, `20260711000000…:29-30`, `20260711020000…:14,36`, `20260716120000_faz7_fortune_log.sql:18`, `20260717150000_chat_threads.sql:17`, `20260719120000_idol_personas.sql:29,46`, `20260810120000…:18`, `20260910120000_plan_events_agent.sql:62-63`, `20260913131020_plan_step_events.sql:69` | Policy | A: değişmez. B: Standart Postgres'te RLS vardır ama "bypass" için uygulama rolü **tablo sahibi** veya `BYPASSRLS` olmalı; aksi hâlde hiçbir satır okunamaz. Karar: ya `enable row level security` satırları atlanır (tek istemci backend) ya da `niyetsen_app` rolü sahipliğiyle oluşturulur. Dokümante edilmeli. | orta |
| 31 | `revoke all on all tables/sequences in schema public from anon, authenticated` + `alter default privileges … revoke` (PostgREST savunması) | `20260820221500_revoke_client_grants_drop_proofs_writes.sql:5-10` | Policy | A: değişmez. B: roller yoksa migration hata verir → koşullu veya atlanır. | düşük |
| 32 | `gen_random_uuid()` varsayılanları — migration'larda hiç `create extension` yok; Supabase'in önkurulu `pgcrypto`/`uuid-ossp`'sine güveniliyor (doğrulama sorgusu 4 extension bekler) | `20260711000000…:18`, `20260711020000…:17`, `20260716120000…:5`, `20260717150000…:6`, `20260719120000…:6,34`, `20260910120000…:18,43`; `RUN_IN_SUPABASE_SQL_EDITOR.sql:360-366` | DB | A: değişmez. B: Postgres ≥13'te `gen_random_uuid()` yerleşik; `uuid-ossp` kullanılmıyor. İlk migration'a `create extension if not exists pgcrypto;` eklemek güvenli tarafta kalır. | düşük |
| 33 | Trigger `plan_event_occurrences_fill()` + `plan_event_occurrences_fill_trg` (`set search_path to 'public'`, `at time zone`, `make_interval`) | `20260913131242_plan_event_occurrences_fill_schedule.sql:16-65` | DB | A/B: standart plpgsql — aynen taşınır. | düşük |
| 34 | Migration defteri `supabase_migrations.schema_migrations` (Supabase CLI/MCP `apply_migration` izi); bazı migration'lar "prod'a MCP ile uygulandı" notu taşır | `RUN_IN_SUPABASE_SQL_EDITOR.sql:369-375`; `20260802160000…:2`, `20260913131242…:2` | DB | A: Supabase CLI `supabase db push` ile aynı tablo. B: defter yok → dbmate/Alembic/sqitch seçilir; mevcut 29 `.sql` dosyası sıra numarasıyla içe alınır (Tuzak #5: migration'lar otomatik uygulanmaz kuralı yeni araçla güncellenir). | orta |
| 35 | Doğrulama script'i Supabase sistem tablolarına bakıyor: `storage.buckets` (public bayrağı), `pg_extension`, `information_schema` grant'leri `anon/authenticated`, `supabase_migrations` | `RUN_IN_SUPABASE_SQL_EDITOR.sql:107-114`, `:163-170`, `:240-248`, `:360-375`, `:397-398` | DB | A: değişmez. B: bölümler 06/07/12/19/32/33 yeniden yazılır (MinIO `mc stat`, `pg_roles`). | düşük |

Bağımlılık **olmayan** noktalar (kontrol edildi): `pgvector` yok
(`20260719120000_idol_personas.sql:32,39` — embedding `float8[]`, kosinüs kodda);
`pg_cron`/`cron.schedule` yok (zamanlama Railway cron, `railway.cron.toml`);
`supabase_realtime` publication yok; `pg_net`/Edge Function yok; `auth.jwt()`/`auth.role()` yok.

---

## 5. Storage (bucket'lar, URL biçimi, doğrudan yüklemeler)

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 36 | Kanıt fotoğrafı yükleme `self._db.storage.from_("proofs").upload(path, bytes, file_options={"content-type", "upsert": "false"})`; yol `{user_id}/{uuid}.{jpg|png}` | `app/storage/supabase_repository.py:633-644` | Storage | A: değişmez. B: `StorageGateway.put(bucket="proofs", key, bytes, content_type)` → S3 `put_object` (`IfNoneMatch="*"` ile upsert=false eşdeğeri). | orta |
| 37 | Sanal adres `storage://proofs/{path}` `proofs.photo_url`'e yazılır; **signed URL üretimi hiçbir yerde yok** (`create_signed_url` rg 0) → fotoğraf istemciye hiç servis edilmiyor, yalnız Vision'a gönderiliyor (doğrulanmalı: başka tüketici bulunamadı) | `supabase_repository.py:645-647`, `app/storage/repository.py:384`; tüketim yalnız `app/api/routes.py:1108-1119` | Storage | A/B: biçim sağlayıcı-bağımsız, değişmez. İleride görüntüleme gerekirse `StorageGateway.presign()` tek nokta olur. | düşük |
| 38 | Hesap silmede kanıt nesnelerini listeleme/silme — storage3 `list(path, options={limit, offset, sortBy})` + 100'lük `remove` | `supabase_repository.py:1222-1256` | Storage | A: değişmez. B: S3 `list_objects_v2(Prefix=f"{user_id}/")` sayfalama + `delete_objects` (≤1000). | orta |
| 39 | Plan görseli için **ayrı** `create_client` + `storage.from_("plan-images").upload(...)`; `USE_SUPABASE_DB`/`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` boşsa `None` döner (yer tutucuya düşer) | `app/services/image_service.py:377-399` (`:387-390`) | Storage/SDK | A: değişmez. B: `StorageGateway` üzerinden `put(bucket="plan-images", key="generated/…")`; her çağrıda yeni istemci yaratma kaldırılır. | orta |
| 40 | **Public URL elle kuruluyor ve DB'ye kalıcı yazılıyor**: `f"{SUPABASE_URL}/storage/v1/object/public/plan-images/{path}"` → `tasks.image_url` → mobil `Image` doğrudan Supabase alan adından yükler | `app/services/image_service.py:395-396` | Storage | A: alan adı değişirse **eski satırlar kırılır** → `UPDATE tasks SET image_url = replace(...)` veya eski host'a 301. B: aynı + CDN/MinIO public base (`STORAGE_PUBLIC_BASE_URL` env). Her iki yolda da veri migrasyonu şart. | yüksek |
| 41 | Smoke test Storage temizliği `repo._db.storage.from_("proofs").remove([...])` | `scripts/smoke_test_supabase.py:152-154` | Storage | A: değişmez. B: `StorageGateway.delete()` ile yeniden yazılır. | düşük |

---

## 6. Mobil (`mobile/src`) — supabase-js kullanımı

**Sonuç: mobil Supabase'i yalnız Auth için kullanıyor.** `supabase.from(`,
`supabase.storage`, `supabase.rpc(`, `supabase.channel(`/realtime,
`functions.invoke` → **0 sonuç**. Tüm veri `src/lib/api.ts` üzerinden FastAPI'ye
bearer token ile gidiyor. Taşınmada istemci Postgres'e/depoya bağlanmayacak; tek iş
kimlik katmanının değişmesi.

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 42 | `@supabase/supabase-js ^2.111.0`; `createClient(url, publishableKey, {auth: {storage: SecureStore-chunk, autoRefreshToken, persistSession, detectSessionInUrl(web), flowType: 'pkce', lock: processLock}})`; env eksikse placeholder ile boot | `mobile/package.json:11`; `mobile/src/lib/supabase.ts:4`, `:10-11`, `:98-116` | SDK/Auth | A: değişmez (URL+anahtar). B: supabase-js kaldırılır → `expo-auth-session` (OIDC Authorization Code + PKCE, Keycloak discovery) + kendi `SessionStore` (SecureStore chunk mantığı korunur) + refresh döngüsü. | yüksek |
| 43 | Anahtar biçimi denetimi: `sb_publishable_`/`sb_secret_` önekleri, legacy JWT `role` claim'i, yasak env adları | `mobile/src/lib/supabase-keys.ts:6-11`, `:26-57`; `mobile/src/lib/app-error.ts:209` (hata metni süzgeci `service_role|sb_secret_|sb_publishable_|supabase`) | SDK | A: değişmez. B: dosya silinir; Keycloak public client'ta gizli anahtar yoktur. Süzgeçte `supabase` kelimesi `keycloak`/yeni host ile genişletilir. | düşük |
| 44 | E-posta + şifre: `signInWithPassword`, `signUp({emailRedirectTo})`, `resend({type:'signup'})` | `mobile/src/providers/auth-provider.tsx:323`, `:336`, `:353` | Auth | A: değişmez. B: Keycloak'ta "Direct Access Grants" (ROPC) mobil için önerilmez → giriş tarayıcı akışına taşınır **veya** kendi auth API'si (bcrypt + e-posta doğrulama) yazılır. Ürün akışı (uygulama içi form) değişir; Şahin kararı gerekir. | yüksek |
| 45 | Şifre sıfırlama / OTP: `resetPasswordForEmail`, `signInWithOtp({shouldCreateUser:false})`, `verifyOtp({type: recovery/email/signup})`, `updateUser({password})`; recovery e-posta şablonu `{{ .Token }}` ile 6 haneli kod | `auth-provider.tsx:367`, `:376`, `:406`, `:426`; `mobile/src/lib/auth-redirect.ts:137` (`token_hash` + `type`) | Auth | A: değişmez (şablonlar self-host GoTrue'ya taşınır). B: Keycloak'ta OTP kodu ile sıfırlama yok → "Şifremi unuttum" e-posta bağlantısı akışı (Keycloak `reset-credentials`) veya kendi OTP tablosu + SMTP. UX yeniden tasarlanır. | yüksek |
| 46 | Google OAuth: `signInWithOAuth({provider, redirectTo, skipBrowserRedirect, queryParams})` + `WebBrowser.openAuthSessionAsync` | `auth-provider.tsx:89-135` (`:91`, `:109`) | Auth | A: değişmez (Google client'ı GoTrue'da yeniden tanımlanır). B: Keycloak Identity Provider = Google; `expo-auth-session` ile `kc_idp_hint=google`. | orta |
| 47 | Apple (iOS native): `AppleAuthentication.signInAsync` → `signInWithIdToken({provider:'apple', token})` | `auth-provider.tsx:469-486` | Auth | A: değişmez. B: Keycloak Apple IdP ile "token exchange" (external IdP token → Keycloak token) özelliği gerekir (doğrulanmalı; Keycloak sürümüne bağlı). Alternatif: tarayıcı akışı (Apple incelemesinde native buton şartı — dikkat). | orta |
| 48 | Deep link dönüşü: `setSession({access_token, refresh_token})` (hash token), `exchangeCodeForSession(code)` (PKCE), `verifyOtp({token_hash,type})`; redirect `niyetsen://auth/callback` "Supabase Redirect URLs ile birebir" | `mobile/src/lib/auth-redirect.ts:9`, `:15-20`, `:104`, `:122`, `:137`; `mobile/src/app/auth/callback.tsx:14-30` | Auth | A: Redirect URL'ler self-host GoTrue'ya kopyalanır. B: Keycloak client "Valid Redirect URIs" = `niyetsen://auth/callback`; yalnız `code` yolu kalır (hash token / token_hash dalları silinir). | orta |
| 49 | Oturum okuma/yenileme → bearer: `getSession`, `refreshSession`, `onAuthStateChange` | `auth-provider.tsx:192-282` (`:226`), `:531` (signOut); `mobile/src/lib/api.ts:164`, `:183`; `mobile/src/lib/gunluk-akis.ts:102`, `:164`; `mobile/src/lib/boot-cache.ts:15`; `mobile/src/lib/analytics.ts:41`; `mobile/src/lib/purchases.ts:165-167`; `callback.tsx:61` | Auth | A: değişmez. B: tek `useSession()`/`getAccessToken()` arayüzü arkasına alınır; `refresh_token` grant Keycloak token endpoint'ine gider. Önce bu sarmalama yapılırsa (Faz 1) geçiş tek dosyaya iner. | orta |
| 50 | `session.user.id` (Supabase auth UUID) üçüncü taraf kimliklerine bağlı: RevenueCat `appUserID`, PostHog `distinctId`, push token kaydı, onboarding taslağı | `purchases.ts:167`, `analytics.ts:42`, `mobile/src/components/onboarding-screen.tsx:145,184,226`, `mobile/src/app/(tabs)/settings.tsx:141` | Auth | A: UUID korunursa değişmez. B: #21 ile aynı kök sorun — kimlik değişirse RevenueCat abonelik eşlemesi ve PostHog geçmişi kopar. **Kullanıcı UUID'si korunmalı.** | yüksek |
| 51 | Env/yapılandırma: `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` 5 EAS profilinde gömülü; i18n `auth.supabaseMissing` metni | `mobile/eas.json:22-23`, `:44-45`, `:62-63`, `:81-82`, `:99-100`; `mobile/.env.example:10-11`; `mobile/src/i18n/locales/tr.ts:72` (+ en-US/de/fr/ar `:72`), `mobile/src/i18n/types.ts:83`; `mobile/src/components/auth-screen.tsx:37`, `:348-350` | Env | A: değerler değişir. B: `EXPO_PUBLIC_AUTH_ISSUER`, `EXPO_PUBLIC_AUTH_CLIENT_ID`; metin anahtarı `authMissing` olarak yeniden adlandırılır. | düşük |

---

## 7. Backend env değişkenleri

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 52 | `SUPABASE_URL` (PostgREST + Storage + JWKS tabanı) | `app/config.py:79`; `.env.example:42` | Env | A: yeni host. B: üçe ayrılır: `DATABASE_URL`, `STORAGE_ENDPOINT`/`STORAGE_PUBLIC_BASE_URL`, `AUTH_JWKS_URL`. | düşük |
| 53 | `SUPABASE_SERVICE_KEY` (alias `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SECRET_KEY`) | `app/config.py:82-86`; `.env.example:46-48` | Env | A: yeni anahtar. B: `DATABASE_URL` şifresi + `STORAGE_ACCESS_KEY/SECRET_KEY` + `AUTH_ADMIN_CLIENT_SECRET`. | düşük |
| 54 | `SUPABASE_TIMEOUT_SEC` (postgrest/storage istemci zaman aşımı) | `app/config.py:87`; `.env.example:68` | Env | B: `DB_STATEMENT_TIMEOUT_MS` / `STORAGE_TIMEOUT_SEC`. | düşük |
| 55 | `USE_SUPABASE_DB` (depo seçimi + prod kilidi + cron direct mod şartı) | `app/config.py:90`; `app/main.py:30-34`; `.env.example:50`, `:70-71`; `scripts/run_scheduled_jobs.py:53-54` | Env | B: `DB_BACKEND=postgres` (bkz. #11). | düşük |
| 56 | Prod sır doğrulaması: `SUPABASE_URL` `https://` ile başlamalı + `SUPABASE_SERVICE_KEY` ≥20 karakter | `app/config.py:202-211` | Env | B: `DATABASE_URL` (`postgresql://`), `STORAGE_*`, `AUTH_JWKS_URL` doğrulaması. | düşük |
| 57 | `SUPABASE_DB_PASSWORD`, `DATABASE_URL`, `DIRECT_URL` — Supabase pooler (`aws-1-ap-southeast-1.pooler.supabase.com:6543/5432`, `pgbouncer=true`) **yalnız örnek dosyada; kod okumuyor** | `.env.example:51-55` | Env | B: `DATABASE_URL` asıl bağlantı olur (PgBouncer varsa transaction modunda prepared statement kapalı — psycopg `prepare_threshold=None`). | düşük |
| 58 | `NEXT_PUBLIC_SUPABASE_URL` → `SUPABASE_URL` geri uyum alias'ı (Railway cron env'i) | `scripts/run_scheduled_jobs.py:25-28`; `scripts/sync_cron_railway_env.py:87-90` | Env | A/B: kaldırılır. | düşük |

---

## 8. Scripts (`niyetsen-backend/scripts/`)

| # | Bağımlılık | Nerede (dosya:satır) | Tür | Taşınma karşılığı (A / B) | Zorluk |
|---|---|---|---|---|---|
| 59 | `smoke_test_supabase.py` — `SupabaseRepository` doğrudan + `repo._db.table(...).delete()` ve Storage `remove` ile temizlik | `scripts/smoke_test_supabase.py:25-32`, `:152-154`, `:181`, `:207-211` | SDK | A: değişmez. B: `smoke_test_db.py` olarak `PostgresRepository` + SQL temizlik ile yeniden yazılır. | orta |
| 60 | `organize_env.py` — `create_client` ile bağlantı testi; `SUPABASE_JWT_SECRET` placeholder; mobil `EXPO_PUBLIC_SUPABASE_*` üretimi | `scripts/organize_env.py:275-278`, `:136-137`, `:83`, `:191`, `:216-217` | SDK/Env | B: bağlantı testi `SELECT 1`; env şablonu yeni adlarla. | düşük |
| 61 | `run_scheduled_jobs.py` — cron "direct" modu `USE_SUPABASE_DB=true` + `SUPABASE_URL` + `SERVICE_KEY` şartı (iş mantığı `repo` üzerinden, dolaylı) | `scripts/run_scheduled_jobs.py:25-58` | Env | B: `DATABASE_URL` şartı; `railway.cron.toml` değişmez. | düşük |
| 62 | `sync_cron_railway_env.py`, `verify_cron_config.py` — Railway cron servisine `SUPABASE_*` kopyalama/doğrulama | `scripts/sync_cron_railway_env.py:87-90`, `:117-120`, `:138-150`; `scripts/verify_cron_config.py:87-96` | Env | B: anahtar listesi güncellenir. | düşük |
| 63 | `verify_kapi3_closure.py` — Supabase smoke testini alt süreç olarak koşturur | `scripts/verify_kapi3_closure.py:50-62`, `:123` | SDK | B: #59'u çağırır. | düşük |
| 64 | `ingest_personas.py` — `repo.upsert_idol_persona` (dolaylı; `NotImplementedError` ile bellek-içi atlama) | `scripts/ingest_personas.py:82-98` | DB | A/B: değişmez (Repository arayüzü). | düşük |

---

## Özet

- **Toplam bağımlılık: 64** (DB/SDK 13 · RPC/grant 5 · Auth-backend 6 · Migration SQL 11 · Storage 6 · Mobil 10 · Env 7 · Script 6).
- **Yüksek zorluk: 8** —
  #1 `supabase-py` → Postgres sürücüsü,
  #3 120 PostgREST çağrısının SQL'e çevrilmesi (`PostgresRepository`),
  #21 `sub` claim'i = `users.id` (kimlik sürekliliği, backend),
  #40 `tasks.image_url` içinde kalıcı Supabase Storage public URL'leri,
  #42 supabase-js auth istemcisi → OIDC/PKCE,
  #44 uygulama içi e-posta+şifre girişi,
  #45 OTP kodlu şifre sıfırlama akışı,
  #50 `session.user.id` ↔ RevenueCat/PostHog bağı (kimlik sürekliliği, mobil).
  (#21 ve #50 aynı kök sorunun iki yüzüdür: **kullanıcı UUID'si korunmadan taşınma yapılmaz.**)
- **Orta: 18**, **düşük: 38**.
- **A yolu (self-host Supabase)** için gerçek iş yalnız: #40 (URL yeniden yazma), #34
  (migration defteri), `auth.users`/Storage nesnelerinin dışa-içe aktarımı ve tüm
  env/anahtarların yenilenmesi. Kod değişikliği neredeyse sıfır.
- **B yolu** için kritik yol: Repository yeniden yazımı (#3) → Storage gateway (#36-40)
  → JWT env'leştirme (#19-20) → mobil auth yeniden yazımı (#42-49) → kimlik
  migrasyonu (#21/#50).
- Mobilde doğrudan DB/Storage erişimi: **yok** (§6).

## Faz 1'de yapılacak hazırlıklar (taşınmadan önce, davranış değiştirmeden)

1. **`StorageGateway` arayüzü** (`app/storage/storage_gateway.py`): `put / delete_prefix / public_url / presign`. `image_service._upload_plan_image` (#39-40) ve `supabase_repository.store_proof_photo` / `_remove_proof_objects` (#36, #38) buna taşınır; ilk implementasyon mevcut storage3 çağrılarını sarar. `STORAGE_PUBLIC_BASE_URL` env'i eklenir, URL elle kurma tek yere iner.
2. **`AuthGateway.delete_user()`** (#22) — GoTrue admin çağrısı sarmalanır; Keycloak/self-host implementasyonu sonra takılır.
3. **JWT ayarları env'den**: `AUTH_JWKS_URL` (boşsa `SUPABASE_URL` türetimi korunur), `AUTH_AUDIENCE` (varsayılan `authenticated`), `AUTH_ISSUER` (opsiyonel doğrulama) — `routes.py:175-208` (#19-20). `organize_env.py:136-137` placeholder silinir (#24).
4. **`league_members.user_id` → `text references public.users(id)`** migration'ı (#25) + `_same_user_id` sadeleşmesi (#12). Supabase üzerinde şimdi yapılabilir; tek `auth.users` bağımlılığı kalkar.
5. **Policy/RLS/grant kararının dokümantasyonu** (#30-31, #18): "tek istemci backend, deny-by-default" ilkesi hedef Postgres'te rol + sahiplik olarak nasıl ifade edilecek — `docs/supabase/SCHEMA_DURUM.md` yanına "hedef rol modeli" bölümü.
6. **Migration defteri kararı** (#34): dbmate/Alembic seçimi; 29 `.sql` dosyası ve `RUN_IN_SUPABASE_SQL_EDITOR.sql` doğrulama bölümlerinin (#35) yeni araca uyarlanma planı. Supabase'e özgü migration'lar (#26-29, #31) `DO $$ … IF EXISTS` ile koşullu hâle getirilir.
7. **Kimlik sürekliliği planı** (#21, #50): hedefte kullanıcı UUID'lerinin aynen korunacağı yöntem (Keycloak import `id` alanı / GoTrue `auth.users` dump) yazılı olarak doğrulanır; gerekirse `users.auth_subject` kolonu için migration taslağı hazırlanır (uygulanmaz).
8. **Mobilde oturum sarmalayıcı** (#49): `getSession/refreshSession/onAuthStateChange` kullanan 8 dosya tek `src/lib/session.ts` arkasına alınır; `supabase` import'u yalnız `auth-provider.tsx`, `auth-redirect.ts`, `session.ts`'te kalır.
9. **`tasks.image_url` envanteri** (#40): kaç satır `…/storage/v1/object/public/plan-images/…` içeriyor — Faz 1'de salt-okunur sayım (`select count(*) from tasks where image_url like '%/storage/v1/object/public/%'`), yeniden yazma script taslağı.
10. Env yeniden adlandırma tablosu (#52-58) `.env.example`'a "V2 hedef adları" yorumuyla eklenir; kod henüz değişmez.

## Doğrulama komutları (bu envanterin üretildiği rg taramaları)

```bash
cd /Users/haze/Desktop/Niyetsen

# 1) Python SDK / PostgREST
rg -n "from supabase|import supabase|create_client|from postgrest|import postgrest|storage3|realtime" niyetsen-backend --type py
rg -n "\.rpc\(|on_conflict=|count=\"exact\"|\.storage\.|auth\.admin|!inner|\.range\(|ClientOptions|create_signed_url|get_public_url|_db\.auth" niyetsen-backend/app/storage/supabase_repository.py
rg -n "app_metadata|admin\.get_user_by_id|admin\.update_user_by_id|admin\.delete_user" niyetsen-backend --type py
rg -c "\.table\(|\.upsert\(|_maybe_single\(" niyetsen-backend/app/storage/supabase_repository.py
rg -n "DATABASE_URL|DIRECT_URL|psycopg|asyncpg|sqlalchemy" niyetsen-backend/app niyetsen-backend/scripts niyetsen-backend/requirements.txt   # → 0

# 2) JWT / JWKS
rg -n "SUPABASE|JWKS|jwks|JWT|aud=|audience|authenticated|service_role" niyetsen-backend/app --type py -g '!app/storage/supabase_repository.py'
rg -n "SUPABASE_JWKS_URL|SUPABASE_JWT_SECRET" niyetsen-backend

# 3) Migration'lar
cd niyetsen-backend/supabase/migrations
rg -n -i "auth\.users|auth\.uid\(\)|auth\.jwt\(\)|storage\.buckets|storage\.objects|storage\.foldername|create policy|drop policy|enable row level security|security definer|create or replace function|create trigger|create extension|grant |revoke |\banon\b|\bauthenticated\b|service_role|supabase_realtime|publication|pg_cron|pgcrypto|uuid-ossp|gen_random_uuid|vector|pg_net" *.sql
rg -n -i "references|on delete" *.sql | rg -v RUN_IN
cd -

# 4) Storage
rg -n "storage://|signed_url|/storage/v1/|from_\(\"proofs\"\)|from_\(\"plan-images\"\)" niyetsen-backend/app mobile/src -g '!node_modules/**'

# 5) Mobil
cd mobile
rg -n "supabase|createClient|signInWithOtp|signInWithOAuth|signInWithPassword|signUp\(|exchangeCodeForSession|resetPasswordForEmail|verifyOtp|onAuthStateChange|getSession|refreshSession|signOut|setSession|flowType|pkce|signInWithIdToken|updateUser" -g '*.ts' -g '*.tsx' -g '!node_modules/**' .
rg -n "functions\.invoke|supabase\.storage|supabase\.from\(|supabase\.rpc|supabase\.channel|supabase\.realtime" src -g '!node_modules/**'   # → 0
rg -n "SUPABASE|supabase" -g '*.json' -g '.env*' -g '!node_modules/**' .
cd -

# 6) Env
rg -n "SUPABASE|JWKS|JWT|STORAGE|BUCKET|S3" niyetsen-backend/.env.example
rg -n "SUPABASE" niyetsen-backend/app/config.py

# 7) Scripts
rg -n "supabase|SUPABASE" niyetsen-backend/scripts/*.py
```

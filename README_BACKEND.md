# Niyetsen Backend — Çekirdek Beyin (V2, 2026-10)

> Bu dizin Niyetsen'in **ana beynidir**: niyet sohbeti → görselli plan,
> puan/ceza/zincir motoru, kanıt doğrulama, fal/mistik, rapor, lig, abonelik
> ve prompt birleştirme burada **çalışır halde** durur. V2 (kurumsal pivot)
> bu çekirdeği değiştirmez; üstüne organizasyon, anket, cüzdan ve çok modelli
> yönlendirme katmanları ekler (hedef mimari: V2 plan §5).
>
> Yol haritası: `docs/NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md` (Faz 0–8) ·
> Kilitli kararlar: `NIYETSEN_MASTER_PLAN.md` §1 · Ajan kuralları: `CLAUDE.md` ·
> Kodun anayasası: `app/core/philosophy.py` (**önce onu oku**).
>
> Bu dosyanın kök kopyası (`/README_BACKEND.md`) birebir aynıdır; birini
> değiştirince diğerini de değiştir.

## Ana felsefe (özet)

Niyetsen'in tek işi: niyeti söze, sözü günlük görevlere, görevleri kırılmayan
bir zincire çevirmek. Kayıp hissi + kimlik evet, suçluluk hayır. En küçük
halka mükemmel günden değerlidir. Plan uydurulmaz, kullanıcının hayatından
türetilir. Fal bir ayna, kader fermanı değil. Kriz anında motivasyon durur,
şefkat devreye girer.
V2 eki: kurumsal panelde de utandırma yok; yönetici tek kişiyi görmez; fal /
mistik / kriz verisi organizasyona akmaz. Tam metin: `app/core/philosophy.py`.

## Hızlı başlangıç

```bash
cd niyetsen-backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # GEMINI_API_KEY vb. .env'e yaz — KODA DEĞİL
pytest -q                   # 381 geçmeli (2026-10-17; anahtar gerekmez, in-memory repo)
uvicorn app.main:app --reload
# Swagger: http://127.0.0.1:8000/docs
```

- Dev'de kimlik: `AUTH_DISABLED=true` iken her isteğe `X-User-Id: <id>` başlığı.
- Unsplash anahtarı yoksa görseller yer tutucuya düşer; halka yine çalışır.
- Gemini anahtarı yoksa AI uçları (`/chat`, `/plan/*`, `/task/{id}/proof`,
  `/fortune/*`) bilinçli `RuntimeError` → 500 verir; oyun motoru (`/me/state`,
  `/cron/close-day`, `/task/{id}/excuse`) anahtarsız çalışır.
- Fiziksel cihazdan (Expo Go) test: `uvicorn app.main:app --host 0.0.0.0
  --port 8000 --reload`; Mac LAN IP'sini `ipconfig getifaddr en0` ile bul, mobil
  `.env`'e `EXPO_PUBLIC_API_URL=http://<LAN_IP>:8000` yaz.

### Uçtan uca çekirdek halka (elle)

1. `POST /chat` → `{"messages":[{"role":"user","content":"bu yıl daha sosyal ve sağlıklı olmak istiyorum"}]}`
2. Model soru sorar; `ready_for_plan: true` olunca →
3. `POST /plan/generate` → görselli ilk parti (`PLAN_BATCH_DAYS`, varsayılan 7 gün).
4. `POST /task/{id}/proof` (foto, ≤ 5 MB) → Vision skoru → `GET /me/state`'te puan.
5. `POST /cron/close-day` (`X-Cron-Secret`) → ceza + zincir işlenir.

## Mimari katmanlar

Kural: **`api/` iş mantığı içermez, `services/` HTTP bilmez, `scoring_service`
DB/HTTP/AI bilmez.** İş mantığı veritabanıyla yalnız `storage/base.py::Repository`
üzerinden konuşur.

```
app/
├── main.py                 Prod kilitleri, CORS, güvenlik middleware'i, global hata yanıtı
├── config.py               TÜM ayarlar env'den; kilitli oyun sabitleri burada
├── api/routes.py           HTTP kapısı — bugün TEK dosya (1803 satır, 61 uç)
├── core/                   prompt, model kapısı, araçlar, yedek çekirdeği (10 modül)
├── services/               iş mantığı (28 modül)
├── storage/                Repository ABC + InMemory + Supabase (4 modül)
└── models/schemas.py       Pydantic API sözleşmeleri (66 sınıf) — mobil tipler buradan
```

### `api/routes.py` — 61 uç (2026-10-17 dekoratör sayımı: 24 GET · 28 POST · 3 PUT · 2 PATCH · 4 DELETE)

| Önek | İçerik |
|---|---|
| `/health` | durum + sürüm (bugün env ve model adlarını da döner — V2 Faz 1'de yalnız `ok` + `version`) |
| `/chat`, `/chat/{greeting,history,session,reset,attachment,threads…}` | ana sohbet, karşılama, oturum/iplik (thread) yönetimi, dosya eki |
| `/plan`, `/plan/{generate,next,ensure-today}`, `/plan/tasks/{id}[/steps]`, `/plan/days/{date}/tasks` | plan üretimi (partili), uzatma, görev düzenleme, alt adımlar |
| `/plan/{plan_id}/events`, `/plan/events/{id}`, `/plan/events/{occ}/complete`, `/plan/{plan_id}/chat[/history]` | plan içi etkinlikler + plan-içi ajan |
| `/task/{id}/proof`, `/task/{id}/excuse`, `/tasks/daily` | kanıt, mazeret, Bugün akışı |
| `/me`, `/me/{state,profile,consent,push-token,subscription[/sync],recap}` | profil, rıza, puan durumu, abonelik, Wrapped rapor |
| `/projects`, `/projects/{new,{id},{id}/activate}` | çoklu plan slotları (ücretsiz = 1 plan) |
| `/bonus/{today,offer,active,{id}/complete}` | fotosuz mikro bonus görevleri (+10) |
| `/fortune/{tarot,horoscope,photo/{kind},chat,history,rights}` | mistik modül, hak sayaçları |
| `/paths`, `/paths/{slug}[/activate]` | İdol Modu — Felsefe Yolları |
| `/league`, `/league/{join,leave}` | opt-in rumuzlu haftalık lig |
| `/cron/{close-day,notifications}` | `X-Cron-Secret` ile korunan gün sonu / bildirim işleri |
| `/webhooks/revenuecat` | imzalı abonelik webhook'u |

Kimlik: `routes.get_current_user` — Supabase JWKS (`/auth/v1/.well-known/jwks.json`,
RS256/ES256, `aud=authenticated`); dev'de `AUTH_DISABLED` + `X-User-Id`.
`DEV_ACCOUNT_EMAILS` abonelik kısa devresi yalnız imzalı `email` claim'inden.

**V2 Faz 1:** `routes.py` ince toplayıcı olur; `api/routers/{chat,plan,proof,
fortune,me,league,billing}.py`'ye bölünür, **yollar değişmez, 381 test kırılmaz**.
Yeni router'lar: `org.py` (`/org/*`), `admin.py` (`/admin/*`), `survey.py`
(`/me/survey`), `wallet.py`, `public.py` (`/public/leads`) — **V2 hedef, Faz 1–4**.

### `services/` — 28 modül (26 `*_service.py` + `bonus_pool.py` + `revenuecat_client.py`)

| Modül | Tek satır |
|---|---|
| `intent_service` | Niyet toplama sohbeti: eksik alanları soruyla doldurur, kriz güvenlik ağı, `ready_for_plan` çifte kilidi (model + kod). |
| `plan_service` | Niyet → Gemini'den yapısal JSON plan → görsel; `PLAN_BATCH_DAYS`'lik partiler (365 gün tek istekte üretilmez). |
| `plan_edit_service` | FAZ 8.3 görev taşı / düzenle / ekle / sil; geçmiş güne taşıma ve tamamlanmış görevi düzenleme yasak; silme ceza tetiklemez. |
| `plan_agent_service` | Plan-içi ajan: hedef planın bağlamı, kapalı araç listesi (`etkinlik_olustur`, `alarm_kur`, `takvime_ekle`), yeni 365 plan üretmez. |
| `event_service` | Plan içi etkinlikler (tek seferlik / tekrarlayan): fotosuz "Yaptım" +50, ceza yok, zinciri korur; hata Bugün akışını düşürmez. |
| `task_step_service` | Plan kartı alt adımları (`plan_step_notes.body` JSON); adım tamamlamak puan yazmaz, zinciri uzatmaz. |
| `task_lifecycle_service` | Görev durumu, puan ve `point_log` tek noktadan değişir; `close_due_users` gün sonu kapanışı (cron). |
| `scoring_service` | **SAF oyun motoru** — DB/HTTP/AI yok; +50, −25×2ⁿ (tavan 200), mazeret −25, taban 0, zincir + jeton. `tests/test_scoring.py` sözleşmesi. |
| `proof_service` | Foto + görev bağlamı → Gemini Vision 0–100 güven; ≥60 onay, <60 nazik tekrar (maks 3, 3.'de beyanla kabul); anlamsal eşleşme zorunlu. |
| `image_service` | `image_keyword` → görsel URL; Unsplash ana, Nano Banana oransal hibrit; **`:387` doğrudan `supabase` istemcisi (plan-images yükleme) → `StorageGateway`'e taşınacak (tek istisna).** |
| `attachment_service` | Sohbet ekleri: PDF/DOCX metin çıkarımı, PNG/JPEG kısa görsel özeti (≤ 5 MB). |
| `greeting_service` | Saat dilimi + kullanıcı bağlamına göre kişisel karşılama (`/chat/greeting`). |
| `tool_service` | Allowlist'li araç dispatcher: model eylem ister, yalnız bu modül geçerliliğe ve sunucu mutasyonuna karar verir. |
| `project_service` | Çoklu plan projeleri: ücretsiz = 1 plan, abonelikle sınırsız yeni niyet; aktif plan slotu. |
| `profile_service` | Profil / onboarding kuralları, doğum tarihi → burç. |
| `consent_service` | Sürümlü, amaca özel yasal rızalar (KVKK, AI sohbet, foto kanıt, pazarlama). |
| `subscription_service` | Deneme ve abonelik erişim kuralları (MASTER_PLAN §1.1, §1.7); dev hesabı muafiyeti. V2: org koltuğu `source: org_seat` (Faz 6). |
| `revenuecat_client` | RevenueCat REST — webhook gecikmesinde abonelik senkronu (`/me/subscription/sync`). |
| `bonus_service` / `bonus_pool` | Sabit, tıbbi olmayan mikro görev havuzu; idempotent bonus akışı (+10, Gemini yok). |
| `notification_service` | Timezone-aware push zamanlayıcı (cron'dan çağrılır); ceza / tarot / recap bildirimleri. |
| `push_service` | Expo Push taşıma katmanı (batch 100, token deseni doğrulama). |
| `fortune_service` | Tarot (3 kart), kahve / el fotoğrafı yorumu, günlük burç, mistik sohbet; `FORTUNE_SYSTEM_PROMPT` + RAG; hak sayaçları; kriz sinyalinde durur; her yanıtta disclaimer. |
| `rag_service` | `knowledge/*.md` → başlık bazlı chunk → Gemini embedding → kosinüs; disk önbelleği; anahtar yoksa keyword fallback; sohbette varsayılan keyword. |
| `path_service` | Felsefe Yolları listesi (`knowledge/idoller.md` tek kaynak). |
| `persona_service` | İdol Modu persona katmanı: Supabase `idol_personas` + `persona_chunks` asıl, `knowledge/personas/*.json` tohum; kişi adı yalnız `source_note`'ta. |
| `recap_service` | Wrapped rapor: kural bazlı (Gemini yok), yalnız kazanımlar; `mirror_line` kural bazlı. V2: "Kurumum" kartı (Faz 2). |
| `league_service` | Opt-in rumuzlu gelişim ligi: yalnız rumuz + puan + zincir; çıkışta üyelik silinir. |

**V2 hedef (Faz 2–3):** `org_service`, `org_analytics_service` (k≥5 guard
servis katmanında), `survey_service`, `wallet_service`, `outbox_service`.
`scoring_service` formülü **değişmez**; yalnız `complete_task` sonrası bayraklı
wallet/outbox kancası eklenir.

### `core/` — 10 modül

| Modül | Rol |
|---|---|
| `philosophy.py` | Anayasa — özellik buradaki yasalarla çelişiyorsa özellik yanlıştır. |
| `prompts.py` | TÜM prompt metinleri: `SYSTEM_PROMPT`, `PROOF_VALIDATION_PROMPT`, `FORTUNE_SYSTEM_PROMPT` (ton değişikliği yalnız burada). |
| `prompt_builder.py` | Değişmez sıra **SYSTEM → CONTEXT (RAG etiketli + KULLANICI BELLEĞİ) → USER**; injection önlemi. V2: `build_memory_block(survey=…, org_context=…)`. |
| `gemini_client.py` | Model çağrısının tek kapısı: retry/backoff/JSON-parse, model fallback, Gemini 3+ için `thinking_level` (`_build_config`). |
| `tools.py` | Function calling **kapalı listesi** (`alarm_kur`, `takvime_ekle`, `gorev_olustur`, `kanit_dogrula`, `puan_guncelle`, `gorev_ertele_mazeretli`, v2: `harita_yer_getir`, `pinterest_gorsel_getir`) + `PLAN_AGENT_TOOL_DECLARATIONS`. |
| `rate_limit.py` | Merkezi, kullanıcı başına HTTP rate limiter (bellek içi — çoklu instance'da Redis, Faz 7). |
| `dev_accounts.py` | `DEV_ACCOUNT_EMAILS` ayrımı: mağaza satın alması olmadan tam erişim. |
| `observability.py` | Sentry init + `capture_exception`. |
| `datetimes.py` | PostgREST'in `str` döndürdüğü timestamptz / ISO değerlerini `datetime`/`date`'e çevirir. |
| `backup.py` | Yedek / geri yükleme çekirdeği (V2 §7.1, Faz 0): env → `BackupConfig`, nesne anahtarı / saklama hesabı, `pg_dump`/`pg_restore` komutları, tablo satır sayısı + md5 snapshot ve karşılaştırma — saf mantık, I/O yok. |

**V2 Faz 1–2:** `model_router.py` (görev → model, env seti, `model_usage_log`)
ve `authz.py` (rol türetme: `org_memberships` + `app_metadata.platform_role`;
k≥5 guard). Rol asla `user_metadata`'dan okunmaz.

### `storage/` — 4 modül

| Modül | Rol |
|---|---|
| `base.py` | `Repository` ABC — **tek gerçek arayüz**; yeni backend eklemek = bu sınıfı implemente etmek. |
| `repository.py` | `InMemoryRepository` (dev/test varsayılanı) + çalışma zamanı seçici (`USE_SUPABASE_DB`). |
| `supabase_repository.py` | Postgres kalıcılığı (PostgREST, `service_role`; RLS açık + politika yok; anahtar backend dışına çıkmaz). |
| `db_coerce.py` | PostgREST satırlarını güvenli parse (jsonb dict/str, unique ihlali). |

**Sunucu bağımsızlığı kuralı (V2 kilit 1.2/3):** servislerde `supabase`
import'u **YASAK**; tek mevcut istisna `services/image_service.py:387`
(`from supabase import create_client`) → V2 Faz 1–2'de `storage_gateway.py`
(S3-uyumlu `StorageGateway`: Supabase Storage bugün, MinIO/S3 yarın) altına
taşınır; sonra CI grep kuralı. Yeni tablolarda Supabase'e özel RPC / Edge
Function / `auth.users` FK'si yok; `users.id` ve `plans.id` **TEXT** kalır.
Mevcut `league_members.user_id → auth.users(id)` FK'si `users(id)`'ye taşınır.

## Model matrisi

Tek kapı `core/gemini_client.py`. **Model adı uydurulmaz** — yalnız
ai.google.dev/gemini-api/docs/models listesinden; aşağıdaki V2 kodları
2026-10-13'te doğrulandı (V2 plan §5.5). 2.5 ailesi Google tarafında yalnız
geçmişte kullananlara açık → fallback olarak güvenilmez (V2 R1).

| Görev | Bugün (`config.py`) | V2 hedef birincil → fallback (Faz 1) |
|---|---|---|
| Ana sohbet | `GEMINI_MODEL` = `gemini-3.1-pro-preview` → `gemini-2.5-flash` | `gemini-3.8-flash` → `gemini-3.6-flash` |
| Plan üretimi | `GEMINI_MODEL_PLAN` = `gemini-3.1-pro-preview` → `gemini-2.5-pro` | `gemini-3.1-pro-preview` → `gemini-4-argon` (A/B KAPI geçerse Argon birincil) |
| Kanıt Vision | `GEMINI_MODEL` | `gemini-3.1-pro-preview` → `gemini-3.8-flash` (katılık değişmez, fixture testleri) |
| Plan-içi ajan | `GEMINI_MODEL` | `gemini-3.8-flash` → `gemini-3.1-pro-preview` |
| Fal / mistik | `GEMINI_MODEL` | `gemini-3.8-flash` → `gemini-3.5-flash-lite` |
| Kurumsal içgörü (toplu JSON → 3 cümle) | — | `gemini-4-argon` → `gemini-3.8-flash` (yalnız k≥5 toplulaştırılmış veri) — Faz 3 |
| Rapor "ayna" | kural bazlı | kural bazlı (model yok) |
| Görsel | `GEMINI_MODEL_IMAGE` = `gemini-2.5-flash-image` | `gemini-3.1-flash-image` → Unsplash |
| Embedding | `GEMINI_EMBED_MODEL` = `gemini-embedding-001` | `gemini-embedding-001` (`gemini-embedding-2-preview` değerlendirme) |

V2 env seti: `GEMINI_MODEL_{CHAT,PLAN,VISION,AGENT,FORTUNE,ORG,IMAGE}` +
`*_FALLBACK`, `GEMINI_EMBED_MODEL`; `GEMINI_MODEL` geriye dönük takma ad.
Gemini 3'te `thinking_budget=0` geçersiz → `thinking_level="low"`. Her çağrı
`model_usage_log`'a (Faz 1). Railway'de set edilen `GEMINI_MODEL*` env'leri
koddaki varsayılanı ezer.

## Ortam değişkenleri (adlar `config.py`'den; değer yazılmaz)

| Grup | Değişkenler |
|---|---|
| Sürüm / ortam | `API_VERSION`, `ENV` (`dev`/`prod`), `AUTH_DISABLED` (bugün varsayılan `true`; Faz 1'de `false`), `CORS_ALLOWED_ORIGINS` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_MODEL_PLAN`, `GEMINI_FALLBACK_MODEL`, `GEMINI_FALLBACK_MODEL_PLAN`, `GEMINI_MODEL_IMAGE`, `GEMINI_EMBED_MODEL`, `GEMINI_TIMEOUT_SEC`, `GEMINI_PLAN_TIMEOUT_SEC`, `GEMINI_PROOF_TIMEOUT_SEC`, `GEMINI_IMAGE_TIMEOUT_SEC`, `GEMINI_MAX_RETRIES`, `GEMINI_CHAT_MAX_OUTPUT_TOKENS` |
| Görsel | `UNSPLASH_ACCESS_KEY`, `IMAGE_GEMINI_ENABLED`, `IMAGE_GEMINI_RATIO` |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (takma adlar `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SECRET_KEY`), `USE_SUPABASE_DB`, `SUPABASE_TIMEOUT_SEC` |
| Cron | `CRON_SECRET`, `CRON_SKIP_PUSH`, `CRON_TIME_BUDGET_SEC` |
| Plan / kanıt / limit | `PLAN_BATCH_DAYS`, `MAX_TASKS_PER_DAY`, `CHAT_RATE_LIMIT_PER_MIN`, `PROOF_RATE_LIMIT_PER_MIN`, `PLAN_RATE_LIMIT_PER_MIN`, `FORTUNE_RATE_LIMIT_PER_MIN` |
| RAG | `RAG_ENABLED`, `RAG_EMBEDDINGS_ENABLED`, `RAG_CHAT_EMBEDDINGS`, `RAG_TOP_K` |
| Abonelik | `REVENUECAT_WEBHOOK_SECRET`, `REVENUECAT_API_KEY` (takma ad `REVENUECAT_SECRET_KEY`), `REVENUECAT_ENTITLEMENT_ID` |
| Hukuki metadata | `PRIVACY_POLICY_VERSION`, `KVKK_CONSENT_VERSION`, `AI_CHAT_CONSENT_VERSION`, `PROOF_PHOTO_CONSENT_VERSION`, `MARKETING_CONSENT_VERSION`, `LEGAL_DATA_CONTROLLER`, `LEGAL_CONTACT_EMAIL` |
| Gözlem / hesaplar | `SENTRY_DSN`, `DEV_ACCOUNT_EMAILS`, `CLOSED_TEST_EMAILS` |

Sırlar **yalnız** `.env` (gitignore'da) / Railway değişkenleri; `.env.example`
placeholder taşır. `validate_prod_secrets()` prod'da `GEMINI_API_KEY`,
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` yoksa süreci açmaz. V2 eklenecekler
(Faz 1–2): model env seti, `ORG_MIN_GROUP_SIZE=5`, `WALLET_EARN_RATE`,
`WALLET_CATEGORY_WEIGHTS`, feature flag'ler.

## Migration disiplini, yedek ve geçiş

- DDL **yalnız** `supabase/migrations/` (29 zaman damgalı SQL +
  `RUN_IN_SUPABASE_SQL_EDITOR.sql`). Migration'lar otomatik uygulanmaz: her yeni
  tablo/kolon VERIFY dosyasına eklenir, Şahin SQL Editor'da çalıştırır.
  SQL Editor'a elle DDL yapıştırma biter; Editor yalnız VERIFY içindir.
- Kök `supabase/migrations/` kopyası (1 stub) Faz 0'da silindi — tek kaynak.
- SQL **standart Postgres**; taşınmada aynı dosyalar hedefte `psql` ile koşar.
- `plans.id` TEXT (uuid değil) — FK `plan_id text references public.plans(id)`.
- Supabase'e özel bağımlılıkların dosya:satır envanteri ve taşınma
  karşılıkları: `docs/SUPABASE_BAGIMLILIK.md` (Faz 0, 2026-10-17).
- **Veri kaybı önlem kapısı (V2 §7, Faz 0–1):**
  - `scripts/backup_pg_dump.py` — günlük `pg_dump --format=custom` → S3-uyumlu
    kova (30 gün saklama); `--force` / `--dry-run`. I/O: `scripts/backup_io.py`
    (subprocess + boto3 tembel import), saf mantık: `app/core/backup.py`.
  - `scripts/verify_backup.py` — `snapshot` (tablo başına satır sayısı + md5),
    `compare`, `fetch-latest`, `local-dump`, `drill`; `scripts/restore_drill_local.sh`
    haftalık geri yükleme tatbikatını tek komuta indirir (PostgreSQL 17 ikilileri
    gerekir — Supabase 17.6). `scripts/local_pg_from_migrations.sh` gerçek
    migration'ları vanilla Postgres'te koşar (29/29 hatasız, 2026-10-17).
  - Cron'a bağlı: `run_scheduled_jobs.py` → `backup` adımı (`BACKUP_HOUR_UTC`,
    günde bir; `CRON_SKIP_BACKUP=true` kapatır); cron imajı `Dockerfile.cron`.
    Testler: `tests/test_backup.py`.
  - Sırada (Faz 1–2): `storage_objects` sha256 envanteri, `auth.users` export
    provası. **KAPI 0 = üretim dump'ıyla tatbikat yeşil** (boru hattı stand-in
    ile doğrulandı; üretim koşusu DB şifresi + kova kimliği bekliyor).
- Geçiş günü (Faz 7): dondurma penceresi, kontrol toplamları, çift JWKS 24 sa,
  14 gün salt okunur Supabase → `docs/GECIS_PROTOKOLU.md` (tatbikat kayıtları orada).
- Bağlantı duman testi: `python -m scripts.smoke_test_supabase`.

## Cron (Railway `cron` servisi)

- Config-as-code: `railway.cron.toml` (Dockerfile build, `startCommand =
  python scripts/run_scheduled_jobs.py`, `cronSchedule = */5 * * * *`,
  `restartPolicyType = NEVER`). Dashboard'da yol `/railway.cron.toml` olmalı
  (`railway.toml` değil); yanlışsa uvicorn açılır → 5 dk'da SIGKILL →
  "Deploy Crashed" spam. Tanı: `docs/RAILWAY_SORUN_GIDERME.md`.
- Deploy: `niyetsen-backend/` içinden `railway up --service cron --ci`
  (api ise REPO KÖKÜNDEN `--service api`).
- `scripts/run_scheduled_jobs.py` — direct mod, **her zaman exit 0**
  (SIGTERM'de de), süre bütçesi `CRON_TIME_BUDGET_SEC` (240 sn):
  1. `task_lifecycle_service.close_due_users` — kullanıcı TZ'sinde 23:59'u
     geçen günleri kapatır: sessiz kaçırma cezası, jeton, zincir.
  2. `notification_service.send_penalty_notifications` — cezalanan
     kullanıcılara dürüst tonlu bildirim (`CRON_SKIP_PUSH` ile atlanır).
  3. `notification_service.run_due_notifications` — saatine gelen görev /
     tarot / bonus / recap bildirimleri.
  Env eksikse (`USE_SUPABASE_DB`, `SUPABASE_URL`, servis anahtarı) iş atlanır,
  yine exit 0. Hatalar Sentry'ye `capture_exception` ile düşer.
- Yardımcılar: `pause_railway_cron.py` / `resume_railway_cron.py`
  (`cron_paused.py` ile duraklatma), `sync_cron_railway_env.py`,
  `verify_cron_config.py`, `verify_railway_cron_runtime.py`, `railway_redeploy.py`.
  4. `backup_pg_dump.run_daily` — günlük `pg_dump` yedeği (`BACKUP_HOUR_UTC`
     saatinde, bugünün önekinde nesne yoksa); yapılandırılmamışsa
     `not_configured` ile sessizce geçer, hata diğer adımları etkilemez.
- Cron imajı `Dockerfile.cron` (API imajı + postgresql-client-17);
  `railway.cron.toml` `dockerfilePath` ona bakar.
- **Sırada:** `org_daily_rollups` gece rollup'ı (Faz 3), outbox yayımcı
  (Faz 8) aynı cron servisine eklenir.

## Dokunulmaz kilitler

- **Oyun sabitleri** `config.py`: `POINTS_PER_TASK=50`, `BONUS_POINTS=10`,
  `BASE_PENALTY=25`, `SILENT_PENALTY_CAP=200`, `EXCUSE_PENALTY=25`,
  `EXCUSE_LIMIT=10` (×0.5), `POINTS_FLOOR=0`, `FREEZE_TOKENS_PER_MONTH=1`,
  `CATEGORIES` (6), `RANK_LADDER`, `FORTUNE_DAILY_RIGHTS`, `PROOF_MIN_CONFIDENCE=60`,
  `PROOF_MAX_ATTEMPTS=3`. Değiştirmeden önce `tests/test_scoring.py` ve
  MASTER_PLAN §1. Kurumsal katman formülü değiştirmez; `reward_wallet` ayrı defter.
- **Prompt sırası** SYSTEM → CONTEXT → USER, tek yer `core/prompt_builder.py`;
  kullanıcı mesajı system rolüne karışmaz; RAG etiketli CONTEXT'te.
- **Araç listesi** `core/tools.py` kapalı; yeni araç = ayrı onay.
  `etkinlik_olustur` yalnız `PLAN_AGENT_TOOL_DECLARATIONS`'ta; araç yanıt
  üretilmeden önce sunucuda çalışır.
- **Sırlar** yalnız `.env`; `/health` sırrı/anahtarı asla döndürmez.
- **Prod auth kilidi** `main.py`: `ENV=prod` iken `AUTH_DISABLED=true`,
  `USE_SUPABASE_DB=false`, boş `CRON_SECRET`, boş `REVENUECAT_WEBHOOK_SECRET`
  → import anında `RuntimeError`, süreç açılmaz.
- **chat_threads degrade modu**: thread hatası sohbeti / plan geçişini
  düşüremez (try/except zırhı kaldırılmaz).
- **Kanıt sıkılığı**: anlamsal eşleşme zorunlu (su ≠ meyve tarifi ≤ 40);
  Vision fixture testleri Faz 1'de B4'ü kapatır.
- **Ton**: dürüst yüzleşme evet, utandırma hayır — Wrapped, lig, bildirim ve
  (V2) kurumsal panelde kaçırılanlar gösterilmez.

## Test haritası (`tests/` — 43 dosya, 381 + 21 yedek testi, `conftest.py` `USE_SUPABASE_DB=false` zorlar)

| Alan | Dosyalar |
|---|---|
| Oyun motoru / görev döngüsü / cron | `test_scoring`, `test_task_lifecycle`, `test_task_steps`, `test_plan_dates_and_cron`, `test_cron_direct`, `test_bonus_pool`, `test_bonus_notifications` |
| Sohbet / bağlam / araçlar | `test_chat_guardrails`, `test_chat_history`, `test_chat_reset_and_dev`, `test_chat_threads`, `test_greeting`, `test_today_memory`, `test_attachment`, `test_tools`, `test_upload_and_chat_limits` |
| Plan / proje / görsel | `test_multi_plan`, `test_new_plan_chat_flow`, `test_plan_edit`, `test_plan_events`, `test_plan_extension`, `test_project_service`, `test_image_service` |
| Kanıt | `test_proof_context` |
| Mistik / İdol / RAG | `test_fortune`, `test_idol_mode`, `test_path_detail`, `test_personas`, `test_rag` |
| Rapor / lig / profil / rıza | `test_recap`, `test_league`, `test_profile`, `test_consent` |
| Abonelik | `test_subscription`, `test_paywall_routes`, `test_revenuecat_client`, `test_revenuecat_webhook` |
| Güvenlik / altyapı | `test_auth`, `test_backend_hardening`, `test_prod_secrets`, `test_observability`, `test_push_service` |

`test_scoring.py` oyun kurallarının **sözleşmesidir** — kırmızıysa kural
bozulmuştur. **V2 eklenecekler:** `test_org_*`, `test_survey`,
`test_model_router`, `test_wallet`, `test_privacy_k5` (her rollup ucu için
zorunlu; 381 → ~450). Sayı düşürülmez.

## Deploy özeti

- `api`: repo kökünden `railway up --project <id> --environment <id>
  --service api --ci` (rootDirectory `niyetsen-backend`; içeriden çalıştırılırsa
  yol ikiye katlanır, build başlamadan FAILED).
- `cron`: `niyetsen-backend/` içinden `railway up --service cron --ci`.
- Doğrulama: `/health` 200 · yeni uçlar JWT'siz 401 · cron log `exit 0`.
- GitHub push canlıda deploy tetiklemez. Production'da bekleyen staged patch'e
  **`accept-deploy` ASLA** — dashboard'dan discard.
- Ayrıntı: `RAILWAY_DEPLOY.md`, `docs/RAILWAY_SORUN_GIDERME.md`.

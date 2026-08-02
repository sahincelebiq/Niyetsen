# Niyetsen — Play Store öncesi güvenlik denetim raporu

**Tarih:** 2026-08-02  
**Kapsam:** `Niyetsen` (backend+docs) + `mobile/` (ayrı git deposu)  
**Yöntem:** Salt okunur kod/migration/config tarama; tek yazılan dosya bu rapor.  
**Denetçi notu:** Prod Supabase Dashboard / Railway / Play Console durumu kodda görülemez → ilgili maddeler `DOĞRULANAMADI` + manuel checklist.

---

## Yönetici özeti

Uygulama kodunda **doğrulanmış KRİTİK (JWT bypass / başkasının verisini tek istekle çekme / istemci Gemini veya service_role) bulgu: 0**.  
Workspace’te **KRİTİK 1** (açık metin sosyal medya şifreleri, henüz git’e girmemiş).  
**YÜKSEK: 8**, **ORTA: 10**, **DÜŞÜK: 5**.  
Gemini istemcide yok; JWT JWKS ile imzalı; prod boot kilitleri (`AUTH_DISABLED`, `CRON_SECRET`, webhook) güçlü; WebView/galeri picker yok.  
**Karar: Bu haliyle Play’e çıkılmamalı.** Önce K-01 (şifre rotasyonu + dosyaları repo dışına), sonra YÜKSEK engelleyiciler ve manuel checklist.

---

## Yayın engelleyiciler

| # | Bulgu ID | Gerekçe |
|---|----------|---------|
| 0 | K-01 | Workspace’te Instagram/TikTok e-posta+şifre açık metin (untracked RTF/zip) — yanlışlıkla commit/iCloud sızıntısı. |
| 1 | H-01 | Onaylı kanıt fotoğrafında EXIF/GPS strip yok → ev konumu Gemini’ye ve Storage’a gidebilir (KVKK + Data Safety). |
| 2 | H-02 | 3. kanıt denemesinde Vision atlanıp beyanla otomatik onay → streak/puan hilesi. |
| 3 | H-03 | `ChatMessage.content` uzunluk sınırı yok → Gemini maliyet DoS. |
| 4 | H-04 | SlowAPI kimlik/limit in-memory → Railway birden fazla replica’da limit zayıflar (maliyet). |
| 5 | H-05 | Prod’da RLS’in gerçekten açık olduğu **DOĞRULANAMADI** — kapalıysa anon key ile tablo sızıntısı KRİTİK olur. |
| 6 | H-06 | Authenticated kullanıcı `proofs` bucket’ına kendi klasörüne doğrudan yazabilir (Vision/backend bypass storage spam). |
| 7 | H-07 | Play Data Safety / KVKK’da Gemini’ye foto+profil aktarımı beyanı kod dışı — form doldurulmadan çıkış riski. |
| 8 | H-08 | `npm audit --production`: 3 high — yayın öncesi giderilmeli veya risk kabulü yazılı olmalı. |

---

## Tüm bulgular (önem sırası)

| ID | Önem | Dosya:Satır | Bulgu | Nasıl istismar edilir | Düzeltme |
|----|------|-------------|-------|------------------------|----------|
| K-01 | KRİTİK | `Sosyal Medya hesap bilgileri/Sosyal medya bilgileri.rtf` (satır 8–9); `Sosyal Medya hesap bilgileri.zip` — **git untracked (`??`)** | Instagram + TikTok hesap e-posta/telefon ve **açık metin şifre** workspace’te. `.gitignore` bu yolu kapsamıyor. | `git add .` / yedek / Cursor sync ile uzak repoya veya paylaşılan diske düşer → marka hesap ele geçirme. | Hemen şifreleri döndür (Instagram+TikTok); dosya/zip’i proje dışına taşı veya sil; kök `.gitignore`’a `Sosyal Medya*` ekle; asla commit etme. Rapor şifreleri tekrar etmez. |
| H-01 | YÜKSEK | [`proof_service.py:29-37`](niyetsen-backend/app/services/proof_service.py); [`routes.py:615-640`](niyetsen-backend/app/api/routes.py); [`supabase_repository.py:481-495`](niyetsen-backend/app/storage/supabase_repository.py) | `validate_upload` yalnız mime+magic byte; EXIF/GPS strip yok. Onay sonrası ham bayt Storage’a yazılır; Vision’a da ham görüntü gider. | Kullanıcı (veya çalıntı oturum) GPS’li foto yükler → konum Google Gemini’ye ve private bucket nesnesine gömülü kalır; cihaz/yedek/sızıntıda ev adresi çıkar. Form ile lat/lon ayrıca da kabul ediliyor (`routes.py:550-580`). | Onay öncesi Pillow/piexif ile yeniden encode (EXIF sil); konum yalnız açık rıza + ayrı alan; Data Safety’de konum+görsel+AI paylaşımı işaretle. |
| H-02 | YÜKSEK | [`proof_service.py:53-59`](niyetsen-backend/app/services/proof_service.py) | `attempt_no >= PROOF_MAX_ATTEMPTS` iken Vision çağrılmadan `approved=True`. | Premium kullanıcı aynı göreve 3 geçersiz kare gönderir → 3.’de +50 puan/zincir. Oyun ekonomisi bozulur. | 3. denemede hâlâ Vision zorunlu tut veya düşük puanlı “beyan” yolu; perceptual hash ile aynı kare tekrarını reddet. |
| H-03 | YÜKSEK | [`schemas.py:19-22`](niyetsen-backend/app/models/schemas.py); [`intent_service.py:153-183`](niyetsen-backend/app/services/intent_service.py) | `ChatMessage.content: str` — `max_length` yok; history Gemini’ye gidiyor. | Auth’lu hesapla çok büyük mesaj / uzun history → token patlaması, fatura şişmesi. Rate limit 10/dk var ama tek istek boyutu sınırsız. | `content` için `max_length` (ör. 4000); istek toplam karakter tavanı; fazla history kes. |
| H-04 | YÜKSEK | [`rate_limit.py:11-32`](niyetsen-backend/app/core/rate_limit.py); [`main.py:66-67`](niyetsen-backend/app/main.py) | Limiter varsayılan in-memory; Redis/storage_uri yok. | N replica’da limit ×N; saldırgan chat/proof/fal ile Gemini kotasını hızla eritir. | Redis (veya eşdeğeri) shared limiter; kullanıcı başına günlük Gemini çağrı tavanı + kill switch. |
| H-05 | YÜKSEK | Migration’lar RLS enable ediyor (ör. [`20260707000000_niyetsen_core_tables.sql:61-67`](niyetsen-backend/supabase/migrations/20260707000000_niyetsen_core_tables.sql)); **prod uygulama durumu kodda yok** | Tasarım: RLS açık + çoğu tabloda policy yok = anon/authenticated PostgREST’ten deny. Prod’da migration uygulanmadıysa RLS kapalı kalabilir. | Anon key (bundle’da meşru) ile `users`/`tasks`/`point_log` dump — klasik Supabase faciası. | Aşağıdaki SQL’leri prod’da çalıştır; RLS kapalı tablo kalmasın. |
| H-06 | YÜKSEK | [`20260711000000_faz3_task_loop.sql:47-85`](niyetsen-backend/supabase/migrations/20260711000000_faz3_task_loop.sql) | `proofs` bucket private; ama `authenticated` için insert/update/delete/select own-folder policy var. Backend de service_role ile yazıyor. | Çalıntı JWT ile kullanıcı kendi `user_id/` altına 5MB×N spam yükler (Storage maliyeti). Puan için hâlâ API gerekir; yine de DoS. | İstemci doğrudan Storage yazmasın: storage insert policy’yi kaldır veya yalnız service_role; mobil yalnızca API upload. |
| H-07 | YÜKSEK | Consent var ([`routes.py:1038-1061`](niyetsen-backend/app/api/routes.py); legal [`legal.ts`](mobile/src/constants/legal.ts)); **Play Data Safety formu repo’da yok** | Foto+sohbet+profil Gemini’ye (yurt dışı) gidiyor; form/beyan Dashboard’da. | Store reddi / KVKK şikâyeti. | Data Safety: fotoğraflar, kişisel bilgiler, AI üçüncü taraf; aydınlatmada Gemini/Google aktarımı açık yaz. |
| H-08 | YÜKSEK | `npm audit --production` (mobile, 2026-08-02) | 3 high (`brace-expansion`, `fast-uri`, `postcss` zinciri), 20 moderate. | Zincire bağlı build-time/config plugin riski; exploitable yüzey sürüme göre değişir. | `npm audit fix` + Expo uyumlu yükseltme; kalamayanlar için yazılı risk kabulü. |
| M-01 | ORTA | [`niyetsen-backend/.env.example:52-53`](niyetsen-backend/.env.example) | Gerçek Supabase project ref `postgres.ktweahgrrppmxpdhohdh` + bölge host’u commit’te (şifre placeholder). | Proje kimliği + bölge saldırı yüzeyi daraltır (şifre brute, phishing hedefi). | Placeholder: `postgres.YOUR_PROJECT_REF`; ref’i örnekten çıkar. |
| M-02 | ORTA | [`proof_service.py:29-37`](niyetsen-backend/app/services/proof_service.py) | Magic byte var (iyi); perceptual/file hash ile “aynı foto tekrar” engeli yok (idempotency yalnız aynı istek anahtarı). | Aynı geçerli foto farklı görevlere / günlere yeniden yüklenebilir. | İçerik hash’i (sha256) kullanıcı+görev veya global dedupe. |
| M-03 | ORTA | [`schemas.py:19-22`](niyetsen-backend/app/models/schemas.py); ToolCall `args: dict` | Birçok modelde `extra` forbid yok; chat content sınırsız (H-03 ile ilişkili). | Mass-assignment riski düşük (çoğu endpoint dar şema) ama gevşek yüzey. | Kritik modellerde `model_config = ConfigDict(extra='forbid')`. |
| M-04 | ORTA | [`main.py:61-65`](niyetsen-backend/app/main.py) | Prod’da `/docs` / OpenAPI kapatılmamış. | API keşfi kolaylaşır (auth yine gerekir). | `docs_url=None` when `ENV=prod`. |
| M-05 | ORTA | [`routes.py:197-204`](niyetsen-backend/app/api/routes.py) | `/health` auth’suz; `env`, model adlarını döner. | Keşif bilgisi. | Prod’da minimal `{status:ok}` veya internal-only. |
| M-06 | ORTA | [`config.py:64`](niyetsen-backend/app/config.py) | `AUTH_DISABLED` varsayılan `true` (dev). Prod kilidi [`main.py:23-27`](niyetsen-backend/app/main.py) var. | `ENV` yanlışlıkla `dev` kalırsa X-User-Id ile kimlik taklidi. | Railway’de `ENV=prod` alarmı; staging ayrı proje. |
| M-07 | ORTA | [`mobile/.gitignore`](mobile/.gitignore); kök [`.gitignore`](.gitignore) | Mobil: `*.jks` var, `google-services.json` yok. Kök: backend `.env` backend gitignore’da; `*.keystore` yok. | Yanlışlıkla commit riski. | `google-services.json`, `*.keystore` ekle. |
| M-08 | ORTA | [`legal.ts:118`](mobile/src/constants/legal.ts); onboarding kodu | 18- için teknik yaş kapısı yok; yalnız metin uyarısı. | Reşit olmayan kullanım / KVKK. | Doğum tarihi ile yaş kontrolü veya “18+” onayı. |
| M-09 | ORTA | [`app.json`](mobile/app.json) android permissions | CAMERA, CALENDAR, BILLING — Photo Picker/`READ_MEDIA` yok (iyi). `targetSdk` / `allowBackup` / `usesCleartextTraffic` prebuild öncesi **DOĞRULANAMADI** (managed; `/android` yok; cleartext bayrağı set edilmemiş). | API 36 zorunluluğu (2026-08-31+) kaçabilir; backup true ise adb veri. | EAS production profilinde `targetSdkVersion: 36`, `android:allowBackup=false`; cleartext kapalı kalsın. |
| M-10 | ORTA | [`main.py:71-80`](niyetsen-backend/app/main.py) | `ENV=dev` ve `CORS_ALLOWED_ORIGINS` boşken `allow_origins=["*"]` (+ methods/headers `*`). Prod’da yalnız env listesi. | Staging yanlışlıkla `ENV=dev` + tarayıcı istemci → herhangi origin’den credential’lı istek yüzeyi (JWT çalınırsa). Mobil native CORS’a bağlı değil. | Prod/staging’de `ENV=prod` + dar CORS listesi; asla prod’da `*`. |
| D-01 | DÜŞÜK | [`rate_limit.py:18-20`](niyetsen-backend/app/core/rate_limit.py) | Limit anahtarı için `verify_signature=False` decode — auth hâlâ JWKS. | Sahte JWT ile rate bucket manipülasyonu (auth 401). | Bilinçli; istersen sadece hash(token). |
| D-02 | DÜŞÜK | [`20260716000000_plan_images_bucket.sql:1-17`](niyetsen-backend/supabase/migrations/20260716000000_plan_images_bucket.sql) | `plan-images` public read. | Plan kartı görselleri herkese açık (PII değil, AI/Unsplash). | UUID path koru; yazma service_role kalsın (şu an öyle). |
| D-03 | DÜŞÜK | Babel `remove-console` | `babel.config.*` yok; prod console strip **DOĞRULANAMADI**. `src/` içinde `console.log` yok; `warn` (supabase/sentry). | Log’da e-posta/token sızıntısı ihtimali. | Metro/babel plugin ile prod’da console kaldır. |
| D-04 | DÜŞÜK | pip-audit | Komut: `pip-audit` / `.venv/bin/pip-audit` → **DOĞRULANAMADI** (araç yok). | Bilinmeyen CVE. | CI’da `pip-audit -r requirements.txt`. |
| D-05 | DÜŞÜK | [`api.ts`](mobile/src/lib/api.ts) üst yorum | Yorum “user id AsyncStorage” diyor; gerçek oturum native’de SecureStore + Bearer. | Denetçi yanlış “JWT AsyncStorage’ta” bulgusu üretebilir. | Yorumu SecureStore gerçeğine güncelle (dokümantasyon). |

### Bilinçli güçlü kontroller (bulgu değil — bağlam)

| Kontrol | Kanıt |
|---------|--------|
| İstemci Gemini yok | `mobile/src` içinde `generativelanguage` / `GoogleGenerativeAI` / `GEMINI_API_KEY` eşleşmesi yok (rg). |
| service_role mobilde reddedilir | [`supabase-keys.ts:25-51`](mobile/src/lib/supabase-keys.ts); `scripts/verify-env.mjs` |
| JWT imza + aud + sub | [`routes.py:173-191`](niyetsen-backend/app/api/routes.py) — `verify_signature=False` yok |
| Prod boot kilitleri | [`main.py:22-46`](niyetsen-backend/app/main.py) |
| Oturum native SecureStore | [`supabase.ts:74-96`](mobile/src/lib/supabase.ts) (web: AsyncStorage — beklenen) |
| WebView yok | `mobile/src` içinde `react-native-webview` / `WebView` import yok; dış link `expo-web-browser` |
| Galeri picker yok | Kanıt/fal: `expo-camera` in-app; `expo-image-picker` yok |
| Task IDOR engeli | [`supabase_repository.py:346-352`](niyetsen-backend/app/storage/supabase_repository.py) `plans!inner` + `user_id` |
| `puan_guncelle` puan yazmaz | [`tool_service.py:97-101`](niyetsen-backend/app/services/tool_service.py) |
| Prompt CONTEXT etiketi | [`prompt_builder.py:62-72`](niyetsen-backend/app/core/prompt_builder.py) |
| Upload magic bytes | [`proof_service.py:19-37`](niyetsen-backend/app/services/proof_service.py) |
| Hesap silme | [`routes.py:1065-1071`](niyetsen-backend/app/api/routes.py) + mobil settings `deleteAccount` |
| Consent gate | `ConsentGate` + `/me/consent`; legal: privacy/kvkk/consent/terms |
| Bonus RPC yalnız service_role | [`20260711020000_push_and_bonus.sql:73-76`](niyetsen-backend/supabase/migrations/20260711020000_push_and_bonus.sql) |

### EXPO_PUBLIC_* envanteri (bundle’a gömülür — beklenen)

| Değişken | Herkese açık olabilir mi? |
|----------|---------------------------|
| `EXPO_PUBLIC_API_URL` | Evet (API origin) |
| `EXPO_PUBLIC_SUPABASE_URL` | Evet |
| `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Evet (anon; RLS şart) |
| `EXPO_PUBLIC_POSTHOG_KEY` / `_HOST` | Evet (client analytics) |
| `EXPO_PUBLIC_SENTRY_DSN` | Evet (genelde public DSN) |
| `EXPO_PUBLIC_REVENUECAT_*_API_KEY` | Evet (RC public SDK key; secret değil) |
| `EXPO_PUBLIC_RC_ENTITLEMENT_ID` / paket id | Evet |
| service_role / `GEMINI_API_KEY` | **Hayır — mobilde yok (doğrulandı)** |

`eas.json` env: yalnız `EXPO_PUBLIC_RC_ENTITLEMENT_ID=premium` — sır değil.  
`app.json` `extra`: EAS `projectId` — sır değil.

### Git geçmişi / .gitignore

| Kontrol | Sonuç |
|---------|--------|
| `git ls-files` `.env` | Tracked değil; tracked: `niyetsen-backend/.env.example`, mobil `.env.example` |
| `git check-ignore` `.env` | backend + mobile ignore ✅ |
| `git log -S "AIzaSy"` | Eşleşme yok (kök + mobile) |
| `git log -- "*.env*"` | Yalnız example/chore commit’leri; gerçek `.env` içerik dump’ı bu taramada görülmedi |
| `.gitignore` keystore | mobile: jks/p8/p12; kök/backend: eksik kalıplar (M-07) |

### service_role kullanım yerleri (backend — RLS bypass gerekli mi?)

| Yer | Gerekli mi? |
|-----|-------------|
| [`supabase_repository.py:95-97`](niyetsen-backend/app/storage/supabase_repository.py) tüm DB | Evet — uygulama yetkisi FastAPI’de; tablolarda kullanıcı policy’si yok (deny-by-default). |
| [`image_service.py:301-308`](niyetsen-backend/app/services/image_service.py) plan-images upload | Evet — public bucket’a yazma. |
| RPC grant `service_role` only (proof/bonus) | Evet — anon çağrımasın. |

### Endpoint özeti (auth)

| Grup | Auth | Not |
|------|------|-----|
| `GET /health` | Yok | Bilinçli; M-05 |
| `POST /webhooks/revenuecat` | Webhook secret | [`routes.py:854-864`](niyetsen-backend/app/api/routes.py) |
| `POST /cron/*` | `X-Cron-Secret` | Boş secret prod’da boot fail |
| Diğer tüm iş API | `Depends(get_current_user)` | JWT veya (yalnız AUTH_DISABLED+dev) X-User-Id |

Rate limit dekoratörü olanlar: chat, attachment, plan/generate, proof, subscription/sync, fortune/*.  
Olmayanlar (auth var): history, excuse, state, profile, bonus, threads… — H-04 ile birlikte maliyet yüzeyi.

### RLS tablo envanteri (migration’lara göre)

| Tablo | RLS enable | Policy (table) | Not |
|-------|------------|----------------|-----|
| users, streaks, points, plans, tasks | Evet | 0 | Deny-by-default; backend service_role |
| intents, chat_msgs | Evet | 0 | |
| proofs, point_log | Evet | 0 | |
| user_consents, proof_requests | Evet | 0 | |
| push_tokens, bonus_offers | Evet | 0 | |
| fortune_log, chat_threads | Evet | 0 | |
| idol_personas, persona_chunks | Evet | 0 | |
| storage.objects / proofs | — | own-folder CRUD authenticated | H-06 |
| storage.objects / plan-images | — | public SELECT | D-02 |

`SECURITY DEFINER` fonksiyonlar `SET search_path = public` ile tanımlı (ör. consent/proof/bonus) — boş `search_path` ideal değil ama sabit `public` set edilmiş; grant’ler service_role’a kısıtlı (bonus).

### Prompt injection / LLM

- Kullanıcı mesajı SYSTEM’e karışmıyor; CONTEXT etiketli ([`prompt_builder.py`](niyetsen-backend/app/core/prompt_builder.py)).
- “Bana 1000 puan ver” → `puan_guncelle` sunucuda puan yazmıyor ([`tool_service.py:97-101`](niyetsen-backend/app/services/tool_service.py)).
- Model `user_id` argümanı taşımıyor; dispatch oturum `user_id` kullanıyor.
- Ekran görüntüsü kuralı prompt’ta var ([`prompts.py:253-254`](niyetsen-backend/app/core/prompts.py)) — model kararı; hash yok (M-02).

---

## Düzeltme sırası (bağımlılıklar + süre)

| Sıra | ID | Süre (kaba) | Bağımlılık |
|------|-----|-------------|------------|
| 0 | K-01 | 30 dk | Şimdi: rotate + dosyayı repo dışına; git’e ekleme |
| 1 | H-05 | 1–2 sa (manuel SQL + düzeltme) | Her şeyden önce prod gerçeği |
| 2 | H-06 | 2–4 sa | Storage policy + mobil yol |
| 3 | H-01 | 4–8 sa | Pillow re-encode; rıza metni |
| 4 | H-02 + M-02 | 4–8 sa | Kanıt ekonomisi |
| 5 | H-03 + M-03 | 2–4 sa | Şema limitleri |
| 6 | H-04 | 4–8 sa | Redis + günlük kota |
| 7 | H-07 + M-08 | 1 gün | Hukuk + Data Safety + yaş |
| 8 | H-08 + D-04 | 2–6 sa | Bağımlılık |
| 9 | M-01, M-04, M-05, M-07, M-09, D-03 | 2–6 sa | Sertleştirme |

---

## Manuel yapman gerekenler

### Supabase SQL Editor

```sql
-- 1) RLS kapalı tablolar (boş dönmeli)
select c.relname as table_name
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;

-- 2) RLS açık ama hiç policy yok (bu projede BEKLENEN — service_role mimarisi)
select t.tablename
from pg_tables t
where t.schemaname = 'public'
  and exists (
    select 1 from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = t.tablename and c.relrowsecurity
  )
  and not exists (
    select 1 from pg_policies p
    where p.schemaname = 'public' and p.tablename = t.tablename
  )
order by 1;

-- 3) Tüm policy’ler
select schemaname, tablename, policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname in ('public', 'storage')
order by 1, 2, 3;

-- 4) Bucket public mi?
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets;
```

Beklenen: `proofs.public = false`, `plan-images.public = true`.  
Anon key ile REST’ten `users` select → boş/401/permission denied olmalı.

### Supabase Dashboard (Auth)

- E-posta doğrulama zorunlu mu?
- Min şifre + leaked password protection
- Auth rate limits
- JWT expiry
- Redirect URL allowlist’te `*` var mı?

### Google Cloud / AI Studio

- Gemini faturalandırma (paid tier) açık mı?
- Kota/alarm; API key kısıtı (HTTP referrer işe yaramaz — IP/sunucu kısıtı)

### Railway

- `ENV=prod`, `AUTH_DISABLED=false`, `USE_SUPABASE_DB=true`
- `CRON_SECRET`, `REVENUECAT_WEBHOOK_SECRET`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY` set
- `CORS_ALLOWED_ORIGINS` (web varsa)
- Replica sayısı vs Redis limiter ihtiyacı

### Play Console

- Data Safety: fotoğraf, kişisel bilgi, konum (varsa), AI/Gemini üçüncü taraf
- `targetSdkVersion` 36
- Hesap silme (in-app + web URL)
- Gizlilik politikası URL
- Fal metni: kader/sağlık iddiası yok; “eğlence” disclaimer

### Acil operasyon (K-01)

- Instagram + TikTok şifrelerini **şimdi** değiştir (raporda şifre yok; dosyada var).
- `Sosyal Medya hesap bilgileri/` ve `.zip` dosyasını proje kökünden çıkar / sil.
- `git status` ile bu yolların untracked kaldığını doğrula; asla `git add` etme.

---

## Tekrar test listesi (düzeltmelerden sonra)

1. Prod SQL: RLS kapalı tablo = 0; anon REST dump başarısız.  
2. EXIF’li GPS JPEG → Storage’daki nesnede GPS yok; Gemini’ye giden bayt strip.  
3. 3× bilerek yanlış kanıt → 3.’de otomatik onay **yok** (veya puan yok).  
4. Aynı foto hash ile 2. görevde red.  
5. 100KB+ chat mesajı → 422.  
6. 2 API replica ile rate limit: 10/dk chat aşılamıyor.  
7. JWT’siz `/task/{id}/proof` → 401; başka kullanıcının `task_id` → 404.  
8. Storage’a doğrudan authenticated upload (policy kaldırıldıysa) → fail.  
9. `npm audit --production` high = 0 (veya kabul kaydı).  
10. `pip-audit` CI yeşil.  
11. Hesap sil → Storage + satırlar temiz.  
12. Play Internal testing: Data Safety formu + silme akışı smoke.

---

## Komutlar (DOĞRULANAMADI maddeleri için tekrarlanabilir)

```bash
# İstemci Gemini
rg -n 'generativelanguage|GoogleGenerativeAI|GEMINI_API_KEY' mobile/src

# Sırlar
rg -n 'AIzaSy|service_role' --glob '!.git' --glob '!node_modules' --glob '!.venv' .

# Git
git log --all --full-history -S 'AIzaSy' --oneline
git ls-files '*.env*' '.env*'

# Audit
cd mobile && npm audit --production
# backend: pip install pip-audit && pip-audit -r requirements.txt
```

---

*Bu rapor düzeltme uygulamaz. Düzeltmeler ayrı onayla, tek tek yapılmalıdır.*

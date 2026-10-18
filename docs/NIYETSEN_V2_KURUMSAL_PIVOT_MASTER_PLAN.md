# NİYETSEN V2 — KURUMSAL PİVOT MASTER PLANI

> **Durum: ONAYLANDI v1.0 (2026-10-17, Şahin — "Faz 0'a başlayabilirsin").**
> Onayla birlikte: `NIYETSEN_MASTER_PLAN.md` §1.14 "V2 kilitleri" eklendi,
> `docs/SONRAKI_SIRA.md` kuyruğu bu planın Faz sırasına çevrildi,
> `.cursor/rules/niyetsen-hafiza.mdc` sözlüğüne V2 terimleri girdi.
> Mevcut kilitler (MASTER_PLAN §1, hafıza, Play sprinti) **geçerliliğini korur**;
> V2 kilitleri onların üstüne eklenir, hiçbirini gevşetmez.
> **Aktif faz: FAZ 0** (§13) — ilerleme işaretleri bu dosyadaki kutucuklardadır.
>
> Bu belge **kod gerçeğine** dayanır: backend/mobil/web/Supabase envanteri
> 2026-10-17'de kaynak koddan çıkarıldı (bkz. §2). Pazar verisi:
> `.cursor/skills/niyetsen-kurumsal-pazar/SKILL.md`.

---

## §0. Tek cümle

Niyetsen'in bireysel çekirdeği (niyet → görselli plan → kanıt → puan → zincir)
**aynen kalır**; üstüne **organizasyon katmanı** gelir: şirketler/İK/yöneticiler
çalışanlarının *toplulaştırılmış ve anonim* niyet–aktivite verisini görür,
**kurumsal niyet** tanımlar ("bu yıl ekibin AI kullanımını güçlendirmek"),
çalışan bu niyeti kendi planına bağlar; aynı hesap **mobil + web**'de çalışır;
niyetsen.com vitrin olmaktan çıkıp **giriş kapısı + kurumsal anlatı + blog** olur.

Neden: rapor bölümü az kullanılıyor (inceleme bulgusu). Bireyde rapor "sonuç";
kurumda rapor **ürünün kalbi**. Rapor = Niyetsen'in B2B değeri.

---

## §1. V2 kilitleri (onaylanınca MASTER_PLAN §1'e girer)

### 1.1 Korunanlar (dokunulmaz)
- Oyun kuralları: +50 görev, −25×2ⁿ (tavan 200), mazeret −25, taban 0, zincir
  23:59 TZ, ayda 1 jeton, 6 kategori sabit. **Kurumsal katman puan formülünü
  değiştirmez.**
- Ton: dürüst yüzleşme ✅, utandırma ❌ — **kurumsal panelde de** ("en az aktif
  çalışan" listesi YOK).
- Fal = ayna; fal/mistik/kriz verisi **organizasyona asla akmaz**.
- Mobil ödeme yalnız IAP/RevenueCat; uygulama içinde harici ödeme linki YOK.
- UI: İlkbahar token'ları, hex hardcode yok, Fraunces+Manrope, Reanimated-only,
  `KeyboardAwareView`, 44pt dokunma, title 32 / screenTitle 22 / subtitle 18.
- Prompt sırası SYSTEM → CONTEXT → USER (`core/prompt_builder.py`), araç listesi
  `core/tools.py` dışına çıkmaz (yeni araç = ayrı onay).
- Model adı uydurulmaz; `ai.google.dev/gemini-api/docs/models` doğrulaması şart.

### 1.2 Yeni kilitler
1. **Gizlilik tabanı (KVKK + sektör normu):**
   - Toplulaştırma eşiği **k ≥ 5** (Viva Insights normu). 5 kişiden az
     departman/filtre kombinasyonu için veri **döndürülmez** (servis katmanında,
     SQL view'da değil).
   - Yönetici/İK **tek bir kişinin** görev, plan, sohbet, fal, anket "zayıf yön"
     cevabını **hiçbir ekranda** görmez. Görünen: katılım %, 6 kategori dağılımı,
     zincir ortalaması, kurumsal niyete bağlı ilerleme %, anket toplamları.
   - Çalışan katılımı **davet + açık onay**, geri alınabilir; katılmayan hiçbir
     ürün içi dezavantaj yaşamaz. İş ilişkisinde açık rıza tek başına zayıf
     dayanak (KVKK Kurul 2020/404, 2026/2035) → organizasyon verisi yalnız
     toplulaştırılmış işlenir; bireysel veri işleme dayanağı **kullanıcı
     sözleşmesi**dir, işveren değil.
   - Roller: `owner` / `hr_admin` / `manager` / `member`; her panel okuması
     `org_audit_log`'a yazılır.
2. **Çift yüzey, tek kod:** Expo Router uygulaması hem mobil hem web
   (`app.niyetsen.com`). Ayrı bir Next.js kullanıcı uygulaması YAZILMAZ.
   İK paneli de aynı Expo kodunda `(org)/` rota grubu olarak başlar (web-first,
   `MaxContentWidth`). Faz 3 KAPI'sında tablo/CSV ergonomisi yetmezse paneli
   `apps/panel` (Next.js) olarak ayırma kararı **o zaman** verilir.
3. **Sunucu bağımsızlığı (Şahin, 2026-10-17):** Yakında büyük bir sunucuya
   taşınılacak; Supabase kalıcı değil. Bu yüzden:
   - İş mantığı **yalnız** `app/storage/base.py::Repository` arayüzüyle konuşur.
     Servislerde `supabase` import'u YASAK. Bugün tek istisna:
     `app/services/image_service.py:387` (`from supabase import create_client`,
     plan-images yüklemesi) → `StorageGateway`'e taşınır; sonra CI grep kuralı.
   - SQL **standart Postgres**; Supabase'e özel RPC/Edge Function/`auth.users`
     FK'si **yeni** tablolarda kullanılmaz. (Mevcut `league_members.user_id →
     auth.users(id)` FK'si V2'de `users(id)`'ye taşınır.)
   - Auth: JWT doğrulaması JWKS üzerinden (bugün böyle). Taşınmada sağlayıcı
     değişse de (Keycloak/Ory/kendi auth) `get_current_user` tek nokta.
   - Storage: `proofs` / `plan-images` erişimi `StorageGateway` arayüzüne alınır
     (S3-uyumlu: Supabase Storage bugün, MinIO/S3 yarın).
   - **Veri kaybı önlem kapısı** §7'de (yedek, çift yazım, doğrulama, geri dönüş).
4. **Ödül/entegrasyon için önü açık temel (Şahin, 2026-10-17):** Sosyallik
   (ve diğer kategoriler) puanı arttıkça kullanıcı anlaşmalı yerlerden kahve,
   kıyafet vb. alabilecek. V2 çekirdeğinde **cüzdan + dışa açık olay akışı**
   kurulur; partner entegrasyonları **Faz 8**'de gelir. Kural: oyun puanı
   (`points`) ile harcanabilir bakiye (`reward_wallet`) **ayrı defterlerdir** —
   puan harcanınca rank düşmez (utandırmama + ekonomi ayrımı).
5. **Çok modelli Gemini:** görev bazlı yönlendirme (`core/model_router.py`).
   2.5 ailesi fallback'ten çıkar (Google: 2.5 erişimi geçmişte kullananlarla
   sınırlı). Model matrisi §5.5.
6. **Kayıt sonrası 3 soru** (sıra kilit): amaç → eksik yön → bizi nereden duydun.
   Atlanabilir; `user_surveys`'e yazılır; "eksik yön" yalnız kişiye özel.
7. **Giriş ekranı seçmeli:** "Kendim için" / "Kurumum için (yönetici)".
   İkisi de aynı Supabase Auth (Google + Apple + e-posta); rol sunucuda
   `org_memberships` + `app_metadata.platform_role`'dan türetilir.
   `user_metadata` yetkide **asla** kullanılmaz.

---

## §2. Mevcut durum fotoğrafı (kod gerçeği, 2026-10-17)

| Katman | Gerçek |
|---|---|
| Backend | FastAPI, tek router `app/api/routes.py` (1803 satır, **61 uç**: 24 GET · 28 POST · 3 PUT · 2 PATCH · 4 DELETE — dekoratör sayımı 2026-10-17), **28 servis modülü** (26 `*_service.py` + `bonus_pool.py` + `revenuecat_client.py`), `Repository` ABC + `InMemoryRepository` / `SupabaseRepository`. Backend Postgres'e **doğrudan bağlanmaz** — tüm veri `supabase-py` → PostgREST (`docs/SUPABASE_BAGIMLILIK.md`). `pytest -q` → **381 geçti** (Faz 0 sonrası 402). |
| Auth | `routes.get_current_user`: Supabase JWKS RS256/ES256, `aud=authenticated`; dev'de `AUTH_DISABLED` + `X-User-Id`. `DEV_ACCOUNT_EMAILS` abonelik kısa devresi. Admin/org ucu **yok**. |
| Modeller | `GEMINI_MODEL`=`gemini-3.1-pro-preview` (sohbet+plan), fallback `gemini-2.5-flash`/`2.5-pro`, görsel `gemini-2.5-flash-image`, embed `gemini-embedding-001`. Yönlendirici yok. |
| Supabase | 21 public tablo, **58 kullanıcı**, 59 plan, 93 görev. RLS açık, **politika yok** (deny-by-default; backend service_role). `plans.id` ve `users.id` **TEXT**. Advisor: leaked-password koruması **kapalı** (WARN). 29 migration + VERIFY dosyası. |
| Mobil | Expo SDK 54, expo-router 6, RN 0.81.5, Reanimated 4, RC 10.x, supabase-js 2.111. 5 tab + 17 stack ekran. Auth: e-posta/şifre + OTP + Google + Apple (kodda var; Supabase'de Google/Apple **etkin mi doğrulanmalı**, AUTH_KURULUM "provider not enabled" diyordu). Onboarding 6 adım (bölge/ad/cinsiyet/doğum/bildirim/rıza) — amaç/eksik yön/kaynak **yok**. `web.output: static`, ~34 `Platform.OS==='web'` dalı. `npx tsc --noEmit` **0 hata**. `any` 0, hex hardcode 7 (kamera siyah/beyaz). |
| Web | `website/` saf statik HTML. **Canlı: Hostinger Business** (`hostinger_business_v3`, 2026-07-10'dan beri; NS dns-parking, hCDN) — `vercel.json` kalıntı; `niyetsen-website.vercel.app` hâlâ 200 + indexlenebilir (çift içerik). 19 TR blog yazısı, 5 dilde yasal sayfa, FormSubmit formları, **giriş yok**, backend çağrısı yok. Palet terracotta + Cormorant/Source Sans (uygulamadan farklı). `auth-callback.html` yalnız "kodu uygulamaya gir" sayfası; `.htaccess` `/auth/callback`'i oraya yönlendiriyor (mobil şifre sıfırlama bu URL'e bağlı). |
| RevenueCat | Proje `proj6538cdb0`; ürünler `niyetsen_monthly:monthly` (P1M), `niyetsen_yearly:yearly` (P1Y) aktif; offering `default` (paywall_id null → özel paywall); **0 deney**. Customer Center ayarlarda var. |
| Railway | `api` + `cron` (bkz. hafıza Tuzak #10). |
| Dokümantasyon | `ARCHITECTURE.md` (2.5 model yazıyor), `REPO_MAP.md` (17 migration/175 test), `README_BACKEND.md` (v0.1, 15 test), `mobile/AGENTS.md` (Expo **v57** linki; SDK 54) **bayat**. |

---

## §3. Pazar konumlandırması (özet — detay skill'de)

| Analog | Taşınan kalıp | Niyetsen farkı |
|---|---|---|
| **Wellbees** (TR) | İK paneli: anonim nabız, esenlik puanı, departman kırılımı, 3 aylık rapor, şirketler arası challenge, puan→market | Görev **kanıtlı**, 365 günlük niyet planı, AI rehber ücretsiz |
| **YuLife** (UK) | Opt-in liderlik, düello, HR ROI raporu, puan→ödül | Ceza mekaniği tabanı 0; 6 kategori "karakter" |
| **Viva Insights** | k≥5, farksal gizlilik, opt-out | — |
| **Heltia / Meditopia** (TR) | Kayıt sonrası kişiselleştirme soruları; Slack/Teams entegrasyonu (v3) | — |
| **Lattice / 15Five** | Kaskad hedef (şirket→departman→kişi), haftalık check-in | Oyunlaştırma + kanıt |

Fiyat tabanı: dijital wellbeing **$1–3 / $5–7.5 / $7.5–12+ PEPM**; TR oyuncular
teklif bazlı. Bireysel kilit 150 TL/ay durur. Kurumsal: koltuk/ay, 3 kademe
(Takım ≤25 · Şirket · Kurumsal-teklif) — **rakam Şahin kararı** (§12).

---

## §4. Kişiler ve yolculuklar

| Kişi | Giriş | Gördüğü | Görmediği |
|---|---|---|---|
| **Birey** (mevcut) | "Kendim için" | Sohbet/Bugün/Planım/Zincir/Profil + Rapor (ayna) + varsa "Kurumum" kartı (kurumsal niyete bağlı ilerlemem) | Başkasının verisi |
| **Çalışan (üye)** | Davet kodu / e-posta alan adı → onay | Birey + kurumsal niyetler listesi + takım challenge + (opt-in) kurum ligi | Yöneticinin ne gördüğü dışında hiçbir şey; "neyi görüyorlar" sayfası şeffaf |
| **Yönetici (manager)** | "Kurumum için" | Kendi departmanının **toplu** verisi (k≥5) | Birey satırı |
| **İK / owner** | "Kurumum için" | Tüm departmanlar toplu, kurumsal niyet CRUD, davet/rol, anket, CSV, faturalama | Birey satırı |
| **Platform admin (biz)** | `app_metadata.platform_role=admin` | Organizasyon listesi, kullanıcı sayıları, model kullanım/maliyet, bayraklar, destek araçları | Kullanıcı içeriği (sohbet/fal) — yalnız ihlal incelemesi, loglu |

---

## §5. Hedef mimari

### 5.1 Yüzeyler ve alan adları

```
niyetsen.com          → vitrin + kurumsal anlatı + blog + "Giriş" (statik; Hostinger Business — zaten canlı, §11)
app.niyetsen.com      → Expo web export (kullanıcı uygulaması, aynı kod) — Hostinger alt alan adı, statik SPA
panel.niyetsen.com    → aynı Expo bundle, (org)/ rota grubu (İK/yönetici) — Faz 3 KAPI'sında Next.js'e ayrılabilir
api.niyetsen.com      → FastAPI (Railway → büyük sunucu, §7)
```

"Mikro-frontend" burada **alt alan adı bazlı** ayrımdır (Vercel Microfrontends
paketi Next/SvelteKit/Vite ister; Expo static çıktıyı kapsamaz). Ortak kimlik:
tek Supabase Auth, çerez değil **Bearer JWT** (web ve mobil aynı `lib/api.ts`).

### 5.2 Backend yeniden yapılanma (davranış aynı, dosyalar bölünür)

```
app/api/
  routes.py            → ince: router'ları toplar (yollar DEĞİŞMEZ, testler kırılmaz)
  routers/chat.py, plan.py, proof.py, fortune.py, me.py, league.py, billing.py
  routers/org.py       → YENİ  /org/*
  routers/admin.py     → YENİ  /admin/* (platform_role=admin)
  routers/survey.py    → YENİ  /me/survey
app/core/
  model_router.py      → YENİ  görev→model (§5.5)
  authz.py             → YENİ  rol türetme (membership + app_metadata), k≥5 guard
app/services/
  org_service.py       → organizasyon/üyelik/davet/rol/kurumsal niyet
  org_analytics_service.py → günlük rollup + k≥5 filtre + "ayna" cümlesi (kural bazlı)
  survey_service.py    → 3 soru + bellek bloğu çıktısı
  wallet_service.py    → ödül cüzdanı defteri (Faz 8 partner; çekirdek Faz 2)
  outbox_service.py    → dışa açık olay akışı (integrasyon ön kapısı)
app/storage/
  base.py              → Repository ABC genişler (org/survey/wallet/outbox)
  supabase_repository.py, repository.py (in-memory) → aynı arayüz
  storage_gateway.py   → YENİ  S3-uyumlu dosya erişimi arayüzü
```

Refaktör kuralı: önce router bölme (davranış sıfır değişim, 381 test yeşil),
sonra yeni modüller. Bölme tek commit, tek konu.

### 5.3 Veri modeli (yeni tablolar — standart Postgres, TEXT id'lerle uyumlu)

```
organizations        id uuid PK, slug unique, name, email_domain?, plan_tier,
                     seat_limit, min_group_size int default 5, created_by text→users(id),
                     created_at, deleted_at
org_departments      id uuid, org_id, name, parent_id?, created_at
org_memberships      org_id, user_id text→users(id), role (owner|hr_admin|manager|member),
                     department_id?, status (invited|active|left), consent_version,
                     consented_at, joined_at, left_at, PK(org_id,user_id)
org_invites          id uuid, org_id, code unique, email?, department_id?, role,
                     expires_at, used_by?, used_at
org_intentions       id uuid, org_id, department_id?, title, description,
                     category (6'dan biri)?, starts_on, ends_on, target_metric
                     (participation_pct|tasks_done|streak_avg), target_value,
                     status (draft|active|done), created_by
org_intention_links  org_intention_id, user_id, plan_id text→plans(id), linked_at,
                     PK(org_intention_id,user_id)
user_surveys         user_id text PK, version int, purposes text[], weak_category,
                     weak_note?, heard_from, answered_at, skipped bool
org_daily_rollups    org_id, department_id?, day date, active_members, tasks_done,
                     tasks_missed_silent, tasks_excused, events_done,
                     category_counts jsonb, streak_avg numeric, intention_progress jsonb,
                     PK(org_id, coalesce(department_id), day)   -- cron günlük yazar
org_audit_log        id bigint, org_id, actor_user_id, action, target, ip_hash,
                     created_at
platform_admins      user_id text PK, granted_by, granted_at  (+ app_metadata yansıması)
reward_wallet        user_id text PK, balance int, lifetime_earned int, updated_at
wallet_ledger        id bigint, user_id, delta, reason (earn_task|earn_bonus|redeem|
                     adjust|expire), ref_type, ref_id, created_at
partner_integrations id uuid, slug, name, kind (voucher|api|manual), config jsonb,
                     is_active  (Faz 8 doldurur)
redemptions          id uuid, user_id, partner_id, cost, status (pending|issued|
                     cancelled), code?, created_at (Faz 8)
integration_outbox   id bigint, aggregate (user|org|wallet), event_type, payload jsonb,
                     created_at, published_at?   -- dışa açık olay akışı
```

Kararlar: `users.id`/`plans.id` TEXT kalır (hafıza Tuzak #2). Abonelik alanları
bugün `users` üstünde; B2B için `org_seats` yerine `organizations.plan_tier +
seat_limit` ve kişi bazlı entitlement RevenueCat'te (`grant-customer-entitlement`).
`league_members.user_id → auth.users` FK'si `users(id)`'ye taşınır (sunucu
bağımsızlığı). Her yeni tabloda RLS **açık + politika yok** (backend service_role)
devam eder; web istemcisi Postgres'e **doğrudan bağlanmaz**.

### 5.4 Kimlik ve roller
- Supabase Auth sağlayıcıları: e-posta/şifre+OTP (var), Google (kod var, panelde
  etkinleştir), Apple (iOS zorunlu). Site URL `https://niyetsen.com`, redirect
  `https://app.niyetsen.com/auth/callback`, `https://panel.niyetsen.com/auth/callback`,
  `niyetsen://auth/callback`.
- Giriş ekranı: iki sekme ("Kendim için" / "Kurumum için"). Kurum sekmesi
  kayıt sonrası "Organizasyon oluştur" veya "Davet kodu" adımına gider.
- Rol türetme sunucuda (`core/authz.py`): `platform_admins` tablosu →
  `app_metadata.platform_role` (Supabase admin API ile yazılır, taşınabilir);
  org rolü `org_memberships`. Mobil `useRole()` yalnız **görünürlük** için;
  yetki her zaman sunucuda.
- Leaked password protection **açılır** (advisor WARN).

### 5.5 Çok modelli yönlendirme (`core/model_router.py`)

Doğrulanan model kodları (ai.google.dev, 2026-10-13): `gemini-4-argon` (stable,
1M bağlam), `gemini-3.8-flash` (stable), `gemini-3.6-flash`, `gemini-3.5-flash-lite`,
`gemini-3.1-pro-preview` (preview — hâlâ listede), `gemini-3-flash-preview`,
`gemini-3.1-flash-image` (Nano Banana 2), `gemini-embedding-2-preview`,
`gemini-embedding-001`. **Dikkat:** `gemini-3-pro-preview` kapatıldı; 2.5 ailesi
yalnız geçmişte kullananlara açık → fallback olarak güvenilmez.

| Görev | Birincil | Fallback | Not |
|---|---|---|---|
| Ana sohbet (ücretsiz, sınırsız) | `gemini-3.8-flash` | `gemini-3.6-flash` | Maliyet + hız; ton testleri korunur |
| Plan üretimi (batch) | `gemini-3.1-pro-preview` | `gemini-4-argon` | A/B: Argon'un plan kalitesi KAPI'yı geçerse birincil olur |
| Kanıt Vision (su≠meyve) | `gemini-3.1-pro-preview` | `gemini-3.8-flash` | Katılık değişmez; fixture testleri |
| Plan-içi ajan (araçlar) | `gemini-3.8-flash` | `gemini-3.1-pro-preview` | Function calling testi |
| Fal / mistik sohbet | `gemini-3.8-flash` | `gemini-3.5-flash-lite` | Disclaimer korunur |
| Kurumsal içgörü anlatısı (toplu veri → 3 cümle) | `gemini-4-argon` | `gemini-3.8-flash` | Yalnız **toplulaştırılmış** JSON girer; k≥5 geçmiş veri |
| Rapor "ayna" | kural bazlı (model yok) | — | Şahin kilidi 16 Ağu |
| Görsel üretimi | `gemini-3.1-flash-image` | Unsplash | 2.5-flash-image'den taşınır |
| Embedding | `gemini-embedding-001` | `gemini-embedding-2-preview` değerlendirme | Boyut değişirse `persona_chunks` yeniden gömülür |

Env: `GEMINI_MODEL_CHAT`, `GEMINI_MODEL_PLAN`, `GEMINI_MODEL_VISION`,
`GEMINI_MODEL_AGENT`, `GEMINI_MODEL_FORTUNE`, `GEMINI_MODEL_ORG`,
`GEMINI_MODEL_IMAGE`, `GEMINI_EMBED_MODEL` + `*_FALLBACK`. `GEMINI_MODEL`
geriye dönük takma ad olarak kalır. Gemini 3+ ailesinde `thinking_level`
(mevcut `_build_config` mantığı). `/health` model adlarını **göstermez** (§10).
Maliyet: her çağrı `model_usage_log` (user_id, org_id?, görev, model, token
in/out, ms) → admin panel. "Para yaksın sorun değil" — ama görünür olsun.

### 5.6 Faturalama
- Bireysel: RevenueCat IAP aynen; paywall `paywall.tsx`; Customer Center
  ayarlarda (var). **Deneyler** (RC Experiments) Play ürünü canlı olunca:
  deney 1 = yıllık vurgulu vs aylık vurgulu paywall; metrik `initial_conversion`.
- Kurumsal: ödeme **uygulama dışı**, web panelden — RevenueCat **Web Billing**
  (Stripe altyapılı) veya fatura (Şahin kararı §12). Koltuk aktifken üyeye
  `premium` entitlement RC API ile grant edilir; üye ayrılınca kaldırılır.
  Apple/Play kuralı ihlali yok (uygulama içinde link gösterilmez; "Kurumun
  karşılıyor" rozeti gösterilir).

### 5.7 Analitik ve gözlem
PostHog event'leri genişler: `survey_completed`, `org_created`, `org_joined`,
`org_intention_linked`, `panel_viewed`, `panel_export`, `wallet_earned`.
Sentry aynı. `model_usage_log` admin panelde.

---

## §6. Ürün spesifikasyonları

### 6.1 Kayıt sonrası anket (3 soru, atlanabilir, ~40 sn)
Yeri: `OnboardingScreen` 6 adımdan sonra, `ConsentGate` öncesi değil **sonrası**
(rıza önce). Her soru tek ekran, İlkbahar kartları, ilerleme noktaları.

1. **"Niyetsen'i ne için kullanacaksın?"** (çoklu seçim): Kişisel gelişim ·
   İş/kariyer hedefi · Sağlık ve alışkanlık · Sosyal hayatım · Kurumum davet
   etti · Ekibimi yönetiyorum. → `user_surveys.purposes`; "Ekibimi yönetiyorum"
   seçilirse çıkışta "Organizasyon oluştur" önerisi.
2. **"Kendinde en çok hangi yönü güçlendirmek istersin?"** 6 kategori kartı
   (İrade, İstikrar, Disiplin, Özgüven, Sosyallik, Özsaygı) + isteğe bağlı
   1 satır not. → `weak_category` (**yalnız kişiye**; bellek bloğuna girer;
   org rollup'ına girmez). Ekranda şeffaflık satırı: "Bu cevap sadece sana
   özel; kurumun görmez."
3. **"Bizi nereden duydun?"** (en son): Arkadaş · Kurumum · Sosyal medya ·
   Mağaza araması · Blog/web · Diğer. → `heard_from`.

Sonuç: `build_memory_block`'a `survey` parametresi; ilk sohbet açılışı amaç ve
güçlendirilecek yöne göre kişiselleşir; `yollar` (Felsefe Yolları) listesi o
kategoriye göre sıralanır ("sana uygun veri setleri").

### 6.2 Rapor (bireysel) yenilemesi
Mevcut panel/hikâye korunur. Eklenen kart: **"Kurumum"** (üye ise): bağlı
kurumsal niyet(ler), kişisel ilerleme %, takım ortalaması (k≥5 ise), "kurumun
ne görüyor" bağlantısı. Yalnız kazanım dili.

### 6.3 İK / yönetici paneli (web-first, `(org)/` rota grubu)
| Ekran | İçerik | Kaynak |
|---|---|---|
| Genel bakış | Aktif üye %, bu hafta görev tamamlama, zincir ortalaması, 6 kategori dağılımı (radar), kurumsal niyet ilerleme | `org_daily_rollups` |
| Departmanlar | Kart listesi; k<5 departman "yeterli katılım yok" | rollups + guard |
| Kurumsal niyetler | CRUD, hedef metrik, bağlı üye sayısı, ilerleme | `org_intentions` |
| Katılım & davet | Davet kodu/alan adı, bekleyen davetler, roller, departman atama | memberships/invites |
| Anketler | 3 soru **toplamları** (amaç dağılımı, kaynak dağılımı; "eksik yön" **yok**) | `user_surveys` agg |
| Challenge (v2.1) | Departmanlar arası haftalık challenge (lig altyapısı) | league + org |
| Dışa aktar | CSV (yalnız toplu satırlar) | audit log'a yazar |
| Ayarlar | Ad, logo, min grup boyutu (≥5), veri saklama süresi, DPA/KVKK metni, faturalama | organizations |

Her ekranda sabit alt not: "Veriler toplulaştırılmıştır; 5 kişiden küçük
gruplar gösterilmez."

### 6.4 Platform admin paneli (`/admin`, platform_role=admin)
Organizasyonlar, kullanıcı/plan/görev sayıları, model kullanım + tahmini
maliyet (günlük), hata oranı (Sentry linki), bayraklar (`feature_flags`
tablosu: `org_layer`, `wallet`, `model_argon_plan`), destek: kullanıcı arama
(e-posta → id), abonelik senkron tetikleme. İçerik okuma yok.

### 6.5 Web sitesi (niyetsen.com)
- İki kitle için üst sekme: **Bireyler** / **Kurumlar**. Hero: "Niyetini plana,
  planını kanıta çevir" + "Ekibinin niyetini birlikte büyüt".
- Sayfalar: Nasıl çalışır (niyet→plan→kanıt→zincir→rapor), Kullanım amaçları
  (kitap bitirmek, 1 aylık proje, sosyal hayatı toparlamak, şirket içi hedef),
  Kurumlar (İK paneli, gizlilik tabanı, k≥5 açıklaması, demo talep formu),
  Fiyatlandırma, Blog (19 yazı kalır + "Kurumsal" kategorisi), Yasal (5 dil),
  **Giriş → app.niyetsen.com**, **Panel → panel.niyetsen.com**.
- Palet/font: uygulama İlkbahar (yeşil+mercan, Fraunces+Manrope) **ile
  hizalanır** (Şahin onayı §12). Formlar FormSubmit'ten **kendi API'mize**
  (`POST /public/leads`, KVKK aydınlatma) taşınır.
- Barındırma: hostinger ön inceleme §11'de; statik dosyalar için Hostinger
  uygundur; Expo web ve panel için statik host + API ayrı.

### 6.6 Ödül/entegrasyon temeli (çekirdek Faz 2, partner Faz 8)
- Görev tamamlanınca `scoring_service.complete_task` → `wallet_service.earn`
  (örn. +50 puan → +5 jeton; oran `WALLET_EARN_RATE`, bayrakla kapalı
  başlar). Sosyallik kategorisi ağırlığı artırılabilir (`WALLET_CATEGORY_WEIGHTS`).
- `integration_outbox`'a `task_completed`, `wallet_earned`, `streak_milestone`
  olayları yazılır; `cron` yayımcı (webhook/queue) Faz 8'de bağlanır.
- Partner API yüzeyi (Faz 8): `POST /partners/{slug}/redeem` (client-credentials),
  kupon kodu üretimi, `redemptions` durumu, kullanıcıya "Ödüller" sekmesi
  (Profil altında). Mağaza kuralı: ödül **gerçek para/ödeme** değil, puan
  karşılığı kupon → IAP ihlali değil; yine de App Review notu hazırlanır.

---

## §7. Sunucu bağımsızlığı ve veri kaybı önlem kapısı (ZORUNLU KAPI)

Hedef: Supabase → büyük sunucu (Postgres + S3-uyumlu depo + kendi auth veya
Supabase self-host) geçişi **sıfır kayıpla**, geri dönüşlü.

### 7.1 Şimdiden (Faz 0–1)
1. **Migration disiplini:** DDL yalnız `niyetsen-backend/supabase/migrations/`
   altında, sıralı; SQL Editor'a elle DDL yapıştırma biter. Taşınmada aynı
   dosyalar hedef Postgres'te `psql` ile koşar. Kök `supabase/migrations/`
   kopyası silinir (çift kaynak).
2. **Günlük `pg_dump`** (cron, `--format=custom`) → S3-uyumlu kova + 30 gün
   saklama; haftalık **geri yükleme tatbikatı** (boş Postgres'e restore + satır
   sayısı/`md5` karşılaştırma script'i `scripts/verify_backup.py`).
3. **Storage envanteri:** `proofs`/`plan-images` nesne listesi + sha256 →
   `storage_objects` tablosu (taşınmada eksik dosya tespiti).
4. **Auth dışa aktarım provası:** `auth.users` (id, email, sağlayıcı, created)
   düzenli export; şifre hash'leri Supabase'den alınabilir (bcrypt) — hedef
   auth'a import edilebilirliği Faz 1'de test edilir.
5. **Supabase'e özel bağımlılık listesi** (`docs/SUPABASE_BAGIMLILIK.md` —
   ✅ 2026-10-17, 64 madde / 8 yüksek): Storage policy'leri, `auth.users` FK,
   `auth.admin.delete_user`, JWKS URL, RPC'ler (`claim_proof_attempt`,
   `complete_bonus_offer`) → her biri için A (self-host Supabase) / B (Postgres
   + MinIO + Keycloak) karşılığı yazılı.
6. **`tasks.image_url` envanteri (envanterden çıkan, A yolunda bile şart):**
   plan görselleri `image_service.py:395-396`'da Supabase Storage **public
   URL'si olarak kalıcı yazılıyor** → taşınmada URL yeniden yazımı (veri
   migrasyonu) veya göreli anahtar + çalışma zamanında URL üretimi
   (`StorageGateway.public_url(key)`). Faz 1'de yeni yazımlar göreli anahtara
   geçer; eski satırlar Faz 7'de tek seferlik `UPDATE`.
7. **Kimlik sürekliliği:** JWT `sub` = `users.id` (Supabase auth UUID) ve aynı
   id RevenueCat `appUserID` + PostHog `distinctId`'dir (`purchases.ts:167`,
   `analytics.ts:42`). Hedef auth sağlayıcı **aynı UUID'leri** import etmeli
   (Keycloak `id` alanı set edilebilir; self-host Supabase'de doğal). Ürün
   akışı kararı: uygulama içi e-posta+şifre ve **OTP kodlu şifre sıfırlama**
   Keycloak'ta birebir yok (ROPC önerilmez) → K10 kararında self-host Supabase
   lehine ağır basan madde.

### 7.2 Geçiş günü protokolü (Faz 7)
1. Hedef ortam hazır: migration'lar koştu, `verify_backup.py` yeşil.
2. **Dondurma penceresi** (gece, TZ İstanbul): yazma kapatılır (API 503 +
   mobil "bakım" ekranı; `cevrimdisi-kuyruk` istemcide bekler).
3. Son `pg_dump` → restore → **satır sayıları + tablo md5 + toplam puan
   kontrol toplamları** eşleşmeden açılmaz.
4. Storage senkron (`rclone`) + `storage_objects` sha256 doğrulaması.
5. Auth kesimi: JWKS yeni sağlayıcıya; eski token'lar süresine kadar **her iki
   JWKS** kabul (çift anahtar penceresi 24 sa).
6. DNS/API `api.niyetsen.com` yeni sunucuya; Supabase **salt okunur** 14 gün
   bekler (geri dönüş).
7. KAPI: 24 sa boyunca hata oranı < %1, puan/zincir tutarlılık raporu temiz →
   Supabase kapatılır.

### 7.3 Çift yazım gerekirse
Kullanıcı sayısı dondurma penceresine sığmayacak kadar büyürse (>10k aktif),
`Repository` üstüne `DualWriteRepository` (birincil Supabase, ikincil hedef)
2 hafta çalışır; okuma hâlâ birincil; tutarsızlık raporu günlük.

---

## §8. Değişecek dosyalar (etkilenme haritası)

### Backend (`niyetsen-backend/`)
| Dosya | Değişim |
|---|---|
| `app/api/routes.py` | Router'lara bölünür (yollar aynı); `/health` sadeleşir |
| `app/api/routers/{org,admin,survey,wallet,public}.py` | YENİ |
| `app/core/authz.py`, `app/core/model_router.py` | YENİ |
| `app/core/gemini_client.py` | `_resolve_model` → router'dan; fallback aile mantığı korunur |
| `app/core/prompt_builder.py` | `build_memory_block(survey=…, org_context=…)` |
| `app/core/prompts.py` | `ORG_INSIGHT_PROMPT` (yalnız toplu veri) + anket sonrası açılış varyantı |
| `app/config.py` | Model env seti, `WALLET_*`, `ORG_MIN_GROUP_SIZE=5`, feature flag'ler |
| `app/services/{org_service,org_analytics_service,survey_service,wallet_service,outbox_service}.py` | YENİ |
| `app/services/scoring_service.py` | **Formül değişmez**; `complete_task` sonrası wallet/outbox kancası (bayraklı) |
| `app/services/recap_service.py` | "Kurumum" kartı verisi |
| `app/services/subscription_service.py` | org koltuğu → premium erişim kaynağı (`source: org_seat`) |
| `app/services/notification_service.py` | Kurumsal niyet hatırlatıcıları (ton kuralı aynı) |
| `app/storage/base.py`, `repository.py`, `supabase_repository.py` | Yeni tablolar; `league_members` FK düzeltmesi |
| `app/storage/storage_gateway.py` | YENİ S3-uyumlu arayüz |
| `app/models/schemas.py` | Organization*, Membership*, Survey*, Wallet*, Admin* |
| `supabase/migrations/2026MMDD_*_v2_org_core.sql` vb. | §5.3 tabloları + `model_usage_log`, `feature_flags`, `storage_objects` |
| `supabase/migrations/RUN_IN_SUPABASE_SQL_EDITOR.sql` | VERIFY satırları |
| `railway.cron.toml` | rollup + backup + outbox job'ları |
| `scripts/verify_backup.py`, `scripts/export_auth_users.py` | YENİ |
| `tests/test_org_*.py`, `test_survey.py`, `test_model_router.py`, `test_wallet.py`, `test_privacy_k5.py` | YENİ (381 → ~450) |

### Mobil (`mobile/`)
| Dosya | Değişim |
|---|---|
| `src/components/auth-screen.tsx` (843 satır) | İki sekmeli giriş; bölünür: `auth/role-tabs.tsx`, `auth/forms.tsx` |
| `src/components/onboarding-screen.tsx` | 3 soru adımı eklenir → `onboarding/survey-step.tsx` |
| `src/app/_layout.tsx` | `SurveyGate` (onboarding sonrası, atlanabilir); rol bağlamı |
| `src/app/(org)/_layout.tsx`, `index.tsx`, `departmanlar.tsx`, `niyetler.tsx`, `katilim.tsx`, `anketler.tsx`, `ayarlar.tsx` | YENİ İK paneli (web-first) |
| `src/app/(admin)/*` | YENİ platform admin (web) |
| `src/app/kurumum.tsx`, `davet.tsx` | Üye tarafı: kurumum kartı, davet kodu |
| `src/app/rapor.tsx` (1238) | "Kurumum" kartı; dosya bölünür `rapor/*` |
| `src/app/(tabs)/settings.tsx` (1118) | "Kurumum" QuickChip + "Ödüller" (bayraklı); bölünür |
| `src/lib/api.ts` (1480) | Domain dosyalarına bölünür `lib/api/{core,chat,plan,org,survey,wallet,admin}.ts`; re-export korunur |
| `src/providers/org-provider.tsx`, `role-provider.tsx` | YENİ |
| `src/hooks/use-role.ts`, `use-org.ts` | YENİ |
| `src/components/charts/*` | `react-native-svg` tabanlı radar/bar (web+native) |
| `src/i18n/*.ts` (6 dil) | `org`, `survey`, `wallet`, `admin` blokları |
| `src/constants/theme.ts` | Panel yoğunluk token'ları (`Density.compact`) — hex eklenmez |
| `app.json` / `app.config.js` | web `name`, `scheme` redirect'leri; `MaxContentWidth` panelde 1200 |
| `AGENTS.md` | Expo **v54** docs linki (v57 yanlış) |
| `src/app/fal.tsx`, `(tabs)/daily.tsx` | 7 hex → `Colors.cameraOverlay` token |

### Web (`website/`)
Statik site **yeniden tasarım** (İlkbahar), `index.html` + `kurumlar.html` +
`fiyatlandirma.html` + `nasil-calisir.html`; blog `blog/` aynen; `js/*-form.js`
→ `POST /public/leads`; `auth-callback.html` → `app.niyetsen.com/auth/callback`'e
yönlendirir; `vercel.json` header'ları Hostinger'da `.htaccess`/panel
karşılığına çevrilir (§11).

### Doküman ve Cursor
| Dosya | Değişim |
|---|---|
| `README.md` | **Yeni V2 README** (ürün, iki yüzey, kurulum, çalıştırma, test, deploy, gizlilik tabanı). Eski → `docs/arsiv-planlama/README_v1_2026-10.md` |
| `README_BACKEND.md` | Baştan: mimari, router'lar, model router, Repository, migration disiplini, yedek/geçiş |
| `docs/ARCHITECTURE.md`, `REPO_MAP.md` | Güncellenir (2.5 → 3.x/4; sayılar) |
| `docs/SUPABASE_BAGIMLILIK.md`, `docs/GECIS_PROTOKOLU.md`, `docs/GIZLILIK_TABANI.md` | YENİ |
| `NIYETSEN_MASTER_PLAN.md` §1 | "V2 kilitleri" (onay sonrası) |
| `.cursor/rules/niyetsen-hafiza.mdc` | Sözlük: Organizasyon, Kurumsal niyet, k≥5, Cüzdan, Outbox |
| `.cursor/skills/niyetsen-kurumsal-pazar/` | ✅ oluşturuldu (bu oturum) |
| `.cursor/agents/niyetsen-org-mimar.md`, `niyetsen-gizlilik-denetci.md`, `niyetsen-web-vitrin.md`, `niyetsen-model-router.md` | YENİ alt ajanlar (Faz 0) |
| `.cursor/hooks.json` + `hooks/` | `afterFileEdit` (mobil .tsx → hex/RN-Easing/`any` tarayıcı), `beforeShellExecution` (`railway up` yanlış dizin + `accept-deploy` engeli), `beforeSubmitPrompt` (sır sızıntısı) |

---

## §9. REA (morluto/rea) kullanımı

Klon: `/tmp/niyetsen-research/rea` (MIT, `rea-agents` 6.5.0, Node ≥22.19).
REA = yerel tersine mühendislik MCP'si (APK/JS/web/binary). **Kurulum
(`npx rea-agents setup`) MCP governance gereği Şahin onayıyla** yapılır; bu
oturumda yalnız okundu.

İzinli kullanım alanları (DISCLAIMER + KVKK uyumlu):
- Kendi `niyetsen-v9-play-internal.aab`/APK: izin/manifest denetimi, gömülü
  string/anahtar sızıntısı, kütüphane envanteri (Faz 0 güvenlik taraması).
- Kendi web sitemiz: `inspect_web_page` / `analyze_web_bundle` ile SEO,
  script ve 3. taraf (FormSubmit, gtag) envanteri.
- Rakip **özellik** öğrenimi yalnız herkese açık web/mağaza sayfalarından;
  rakip APK decompile/kod kopyalama **yapılmaz**.

---

## §10. Hata ve risk denetimi (systematic-debugging + review bulguları)

| # | Bulgu | Seviye | Nerede | Aksiyon / Faz |
|---|---|---|---|---|
| R1 | 2.5 fallback'ler Google tarafında **erişim kısıtlı**; `GEMINI_MODEL_IMAGE=gemini-2.5-flash-image` | YÜKSEK | `config.py` | Faz 1: model router + yeni fallback'ler |
| R2 | `/health` env + model adlarını herkese açıyor | ORTA | `routes.py` 226–234 | Faz 1: yalnız `ok`+`version` |
| R3 | Supabase Auth leaked-password koruması kapalı | ORTA | Supabase advisor | 2026-10-18: açmak **Pro** istiyor. Şahin şimdi yükseltmiyor. Captcha açık. Pro olunca e-posta sağlayıcısında aç |
| R4 | Google/Apple sağlayıcıları Supabase'de etkin mi belirsiz (AUTH_KURULUM "not enabled") | YÜKSEK (web giriş) | Supabase dashboard | Faz 0: doğrula/etkinleştir |
| R5 | `league_members.user_id → auth.users(id)` FK + `image_service.py:387` doğrudan `supabase` istemcisi (sunucu bağımsızlığını kırar) | ORTA | `20260810120000` migration, `image_service.py` | Faz 1–2: `users(id)` FK + `StorageGateway` |
| R6 | DDL SQL Editor'a elle yapıştırılıyor; kök `supabase/migrations/` kopya stub | ORTA | Tuzak #5 | Faz 0: tek kaynak + disiplin |
| R7 | Yedek/geri yükleme tatbikatı yok | YÜKSEK (geçiş) | — | Faz 0–1: §7.1 |
| R8 | Rate limiter bellek içi (çoklu instance'da tutmaz) | DÜŞÜK (şimdi) | `rate_limit.py` | Faz 7: Redis |
| R9 | `routes.py` ~1800, `api.ts` 1480, `daily.tsx` 1478, `rapor.tsx` 1238, `settings.tsx` 1118, `auth-screen.tsx` 843 satır | ORTA (bakım) | — | Faz 1–3: bölme (davranış sıfır değişim) |
| R10 | 7 hex hardcode (kamera siyah/beyaz) | DÜŞÜK | `fal.tsx`, `daily.tsx` | Faz 1: token |
| R11 | `mobile/AGENTS.md` Expo v57 linki (SDK 54) | DÜŞÜK | — | Faz 0 |
| R12 | Dokümantasyon bayat (ARCHITECTURE 2.5, REPO_MAP 17/175, README_BACKEND v0.1) | ORTA | docs | Faz 0 yeni README; diğerleri Faz 1 |
| R13 | Web formları FormSubmit (3. taraf, KVKK aydınlatma yok) | ORTA | `website/js/*` | Faz 5: `POST /public/leads` |
| R14 | Web palet/font uygulamadan farklı; `auth-callback.html` gerçek köprü değil | DÜŞÜK→ORTA (pivotta) | `website/` | Faz 5 |
| R20 | Hostinger: blog clean-URL **404**, sitemap 1 yıl cache, `.py`/`vercel.json` herkese açık, HSTS yok, Vercel kopyası indexlenebilir | ORTA–YÜKSEK (SEO/güvenlik) | `website/.htaccess`, yayın arşivi | Faz 0 (§11 H1–H6) |
| R15 | B4 "su≠meyve" KAPI işaretsiz; Data Safety taslağı açık | YÜKSEK (store) | PLAYSTORE_GOAL | Faz 1'de kapanır (model router Vision fixture'ları) |
| R16 | CORS dev'de `*`; `AUTH_DISABLED` varsayılan true (prod kilidi var) | DÜŞÜK | `main.py`, `config.py` | Faz 1: varsayılanı false yap, dev `.env`'e taşı |
| R17 | Abonelik alanları `users` üstünde; B2B koltuk kaynağı yok | ORTA | `users` | Faz 2/6: `source` alanı + org koltuğu |
| R18 | PostHog ham HTTP; org event'leri yok | DÜŞÜK | `analytics.ts` | Faz 3 |
| R19 | Kurumsal veri sızıntı riski: küçük grup + kesişen filtre | **KRİTİK (ürün)** | yeni kod | Faz 2: `test_privacy_k5.py` her rollup ucu için ZORUNLU |
| R21 | `tasks.image_url` kalıcı Supabase Storage public URL'si (taşınmada kırılır) | ORTA (geçiş) | `image_service.py:395-396` | Faz 1: göreli anahtar + `StorageGateway.public_url`; Faz 7: eski satırlar `UPDATE` (§7.1/6) |
| R22 | Kimlik sürekliliği: `users.id` = auth UUID = RC appUserID = PostHog distinctId; OTP şifre sıfırlama Keycloak'ta yok | YÜKSEK (geçiş) | `routes.py:213-220`, `auth-provider.tsx:367-426`, `purchases.ts:167` | K10'da self-host Supabase lehine; aksi hâlde UUID import + OTP akışı yeniden tasarım (§7.1/7) |
| R23 | AAB (v9): `RECORD_AUDIO` izni (expo-camera manifesti ekliyor) + özel scheme deep link'ten `access_token/refresh_token` kabulü (oturum sabitleme) | YÜKSEK (store + güvenlik) | `app.json`, `mobile/src/lib/auth-redirect.ts:100-115` | Faz 1 AAB: `android.blockedPermissions`, implicit token dalı kaldır + `state`, App Links; R8 açık, `PreviewActivity`/`SYSTEM_ALERT_WINDOW` çıkar — `docs/security/AAB_TARAMA_2026-10.md` |

Yeşil taban: `pytest` 381 → **402** (Faz 0) ✅, `tsc` 0 ✅, `any` 0, Reanimated ihlali 0, TODO 0.

---

## §11. Hostinger ön incelemesi (salt okunur alt ajan, 2026-10-17)

**Gerçek:** niyetsen.com **zaten Hostinger'da** (Business planı, sipariş
`1009664904`, apex A `92.113.23.46/.16.244`, `www` → apex 301, TLS geçerli).
"Hostinger'a taşı" bitmiş; kalan iş sertleştirme + web uygulaması hazırlığı.
Statik site için **P0 yok**; frontend'de sır yok (yalnız kamuya açık ID'ler).

### P1 — sonraki yayından önce (`website/.htaccess`)
| # | Sorun | Düzeltme |
|---|---|---|
| H1 | `sitemap.xml`/`robots.txt`/`llms.txt` 1 yıl `immutable` cache'leniyor (`.htaccess:56`) | `txt\|xml` ayrı blok, `max-age=3600` |
| H2 | Vercel `cleanUrls` yok: `/blog/<yazı>` **404**, `.html` 200 (yalnız 8 el yolu eşlenmiş) | Genel fallback: `RewriteCond %{REQUEST_FILENAME}.html -f` → `RewriteRule ^(.+)$ $1.html [L]` |
| H3 | HSTS yok | `Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"` (app./api. HTTPS olduktan sonra) |
| H4 | hCDN her yanıtta `BYPASS` (CSS dâhil) | hPanel → Performance → CDN / cacheless modu kontrol |
| H5 | `/build_legal_pages.py`, `/vercel.json` **herkese açık** 200 | Yayın arşivi allowlist'ten; `.env.local`, `.vercel/`, `.vercelignore`, `.DS_Store`, `.gitignore` dışarıda |
| H6 | `niyetsen-website.vercel.app` hâlâ yayında, noindex yok | Vercel projesini sil veya 308 → niyetsen.com; sonra `vercel.json`/`.vercel/` kaldır |

P2: `Header set` → `Header always set` + `ErrorDocument 404 /404.html`;
`/www → /`; sitemap'te çift `/hesap-silme(.html)`; DMARC `p=none` → Supabase
özel SMTP öncesi sıkılaştır.

### Web uygulaması aşaması (Faz 1/5 kararı)
- `app.niyetsen.com` = Hostinger **alt alan adı sitesi**, statik SPA (Expo web
  export + `.htaccess` `RewriteRule . /index.html`). Node/SSR **gerekmez**;
  VPS **önerilmez** (backend Railway'de).
- Panel aynı bundle'da (`panel.niyetsen.com` ayrı alt alan veya `app.`/panel rotası).
- **Auth URL ayrımı zorunlu:** gerçek PKCE handler
  `https://app.niyetsen.com/auth/callback`; `niyetsen.com/auth/callback` mobil
  şifre sıfırlama bilgi sayfası olarak **kalır** (yoksa mobil akış kırılır).
  Supabase redirect `https://niyetsen.com/**` joker → kesin yollar.
- Railway `CORS_ALLOWED_ORIGINS += https://app.niyetsen.com, https://panel.niyetsen.com`.
- Google OAuth client authorized origins'e `app.niyetsen.com`.
- CSP sıkılaştırılırsa `connect-src`: `*.supabase.co`, Railway API,
  `accounts.google.com`.
- Build-time grep: bundle'da `service_role` / `sb_secret` **yok** (CI).
- DNS: `app` A/CNAME → Hostinger; `api` CNAME → Railway özel alan adı
  (`api.niyetsen.com` testlerde referanslı, bugün çözülmüyor).

---

## §12. Açık kararlar (Şahin)

| # | Karar | Önerim |
|---|---|---|
| K1 | Web paleti İlkbahar'a hizalansın mı? | Evet — app + web tek marka |
| K2 | İK paneli Expo `(org)/` mi, Next.js mi? | Expo ile başla; Faz 3 KAPI'da karar |
| K3 | Kurumsal ödeme: RC Web Billing mi, fatura mı? | Küçük takım: Web Billing; Kurumsal: fatura |
| K4 | Kurumsal fiyat kademeleri (TL/koltuk/ay) | Taslak: Takım ≤25 · Şirket · Teklif; rakam sen |
| K5 | Plan üretiminde `gemini-4-argon` A/B şimdi mi? | Faz 1'de A/B; KAPI geçerse birincil |
| K6 | Vercel kalıntısı (`niyetsen-website.vercel.app`) silinsin mi? | Evet — çift içerik; 308 ile kapat, `vercel.json` kaldır (§11 H6) |
| K7 | Org katılımı: davet kodu mu, e-posta alan adı mı? | İkisi; alan adı yalnız doğrulanmış kurumlarda |
| K8 | Özellik adı: "Niyetsen Kurumsal" / "Niyetsen Ekip" | "Niyetsen Kurumsal" (B2B dili) |
| K9 | Cüzdan kazanım oranı ve Sosyallik ağırlığı | 50 puan → 5 jeton; Sosyallik ×1.5 (bayrak kapalı başlar) |
| K10 | Büyük sunucu hedefi: yönetilen Postgres mi, self-host Supabase mi? | Self-host Postgres + MinIO + Keycloak **veya** self-host Supabase (en az değişiklik) — Faz 7 öncesi |
| K11 | Vercel AI Gateway / AI SDK (`ai` npm, kimi-k3 örneği) kullanılsın mı? (Şahin 2026-10-17'de Vercel onboarding snippet'ini + API anahtarını paylaştı) | **Hayır (F0/F1).** Backend Python + `google-genai`; model router Gemini API'ye doğrudan gider (§5.5, thinking_level / function calling / Vision aynı SDK'da). AI SDK Node içindir, repoda Node backend yok; Prisma da kullanılmaz (`Repository` + migration disiplini). Gateway'in değeri (tek anahtar, maliyet logu) `model_usage_log` ile karşılanır. Faz 4'te maliyet görünürlüğü yetmezse yeniden bakılır. **Chat'e düşen `vck_…` anahtarı rotasyon ister** (transkriptte kalır); dosyaya yazılmadı. |
| K12 | Yedek kovası sağlayıcısı | **Cloudflare R2** (10 GB ücretsiz, çıkış ücreti yok, S3 API) — alternatif Backblaze B2. Hostinger Business'ta S3 nesne deposu yok. Kova özel; yalnız bu kovaya yetkili API anahtarı → Railway `cron` env. |

---

## §13. FAZ PLANI (öncelik sırası, KAPI'lı)

> Kural: KAPI geçmeden sonraki faza başlanmaz. Her faz küçük commit'ler:
> kök `v2: <konu>`, mobil `v2-ui: <konu>`. Commit yalnız Şahin isteyince.

### FAZ 0 — Hazırlık ve zemin (2–3 gün) — *AKTİF, 2026-10-17*
- [x] Bu plan onayı → MASTER_PLAN §1.14 "V2 kilitleri", SONRAKI_SIRA, hafıza sözlüğü. *(2026-10-17)*
- [x] **Yeni `README.md` (V2)** + `README_BACKEND.md` (kök kopya birebir); eski README → `docs/arsiv-planlama/README_v1_2026-10.md`.
- [ ] Supabase (**Şahin — panel**, adımlar `docs/AUTH_KURULUM.md` A7/A9): leaked-password **Pro'ya ertelendi** (2026-10-18, advisor hâlâ WARN; Captcha açık). Google sağlayıcı **etkin — kanıt `auth.identities` 4 google kimliği** (R4'ün Google yarısı ✅); Apple 0 kimlik → iOS öncesi açılacak; redirect URL'leri (`https://app.niyetsen.com/auth/callback`, `https://panel.niyetsen.com/auth/callback`) ekle, `niyetsen.com/**` jokerini kesin yollara indir; Google Cloud web client origins'e `app.`/`panel.`.
- [x] Migration tek kaynak: kök `supabase/migrations/` kopyası kaldırıldı (backend kopyasıyla birebir doğrulandı); `docs/SUPABASE_BAGIMLILIK.md` yazıldı (dosya:satır envanteri, A/B taşınma karşılıkları).
- [x] Günlük `pg_dump` cron (`scripts/backup_pg_dump.py` + `run_scheduled_jobs.py` backup adımı + `Dockerfile.cron` pg 17) + `scripts/verify_backup.py` + `restore_drill_local.sh` + `local_pg_from_migrations.sh` (29/29 migration vanilla PG'de hatasız) + `docs/GECIS_PROTOKOLU.md`; 21 test. **Stand-in tatbikat EŞİT ✅.**
- [ ] **Üretim tatbikatı** (KAPI 0): `.env` `DIRECT_URL` hâlâ `[YOUR-PASSWORD]` → Şahin DB şifresini girer; Railway cron'a `BACKUP_*` + S3 kova kimliği (öneri Cloudflare R2) → `restore_drill_local.sh --from-source` yeşil → GECIS_PROTOKOLU §7'ye kayıt.
- [x] Cursor: 4 alt ajan (`.cursor/agents/niyetsen-{org-mimar,gizlilik-denetci,web-vitrin,model-router}.md`) + `.cursor/hooks.json` + `hooks/` (afterFileEdit/postToolUse hex-Easing-`any`; beforeShellExecution `railway up` dizin + `accept-deploy` deny; beforeMCPExecution `accept-deploy` deny; beforeSubmitPrompt sır deseni). Canlıda doğrulandı (hook deny tetiklendi).
- [x] Kendi AAB güvenlik taraması (REA AAB kabul etmedi → yerel protobuf/Hermes çözücü) → `docs/security/AAB_TARAMA_2026-10.md`: KRİTİK 0 · YÜKSEK 2 (`RECORD_AUDIO` izni, deep-link token kabulü) · ORTA 5 · DÜŞÜK 6. Y-01/Y-02 + O-01..O-05 **F1 AAB'sinde kapanır** (mobil repo işi).
- [x] `mobile/AGENTS.md` v54 düzeltmesi.
- [x] Hostinger P1 kod tarafı: `website/.htaccess` H1 (`txt|xml` 3600) + H2 (clean-URL genel fallback) + H3 (HSTS, includeSubDomains Faz 1'de) + P2 (`Header always`, `ErrorDocument 404` + `404.html`, `/www` 301, yasaklı dosyalar `Require all denied`); H5 `website/scripts/build_release.sh` allowlist (135 dosya, yasaklı 0). **Yerel Apache 2.4 doğrulaması** (macOS httpd, AllowOverride All, 18 istek): `/blog/<yazı>` ve `/blog/<yazı>/` → 200; `/olmayan` → 404 + `404.html`; `txt|xml` → `max-age=3600`; css/png → `immutable`; HSTS her yanıtta; `/vercel.json`, `/build_legal_pages.py`, `/.vercelignore` → 403; `/www` → 301 `/`. (Not: `AddOutputFilterByType` Apache 2.4'te `mod_filter` ister — Hostinger LiteSpeed'de zaten çalışıyor.)
- [x] Hostinger yayın (2026-10-17, Şahin onayı): allowlist zip → `hosting_deployStaticWebsite` + önbellek temizliği. Canlı: `/blog/ertelemek-psikolojisi` 200 + `max-age=600` + HSTS; `/sitemap.xml` `max-age=3600`; `/css/style.css` 1 yıl `immutable`; `/vercel.json` ve `/build_legal_pages.py` 404; olmayan yol 404 + `404.html`. Önbelleksiz mod kapatıldı, site önbelleği açıldı.
- [ ] H4: `x-hcdn-cache-status` hâlâ **BYPASS** (HTML ve CSS, sade `Cache-Control`'e rağmen). API'de CDN ürününü açan/okuyan çağrı yok → hPanel → Performans → CDN.
- [ ] H6 (**Şahin**): `niyetsen-website` (`prj_TQ1q9R4vta4V5pFaKEYg9qSIMxiw`) duraklatma 403 (takım yetkisi yok). `niyetsen-website.vercel.app` 308 veya projeyi sil.
- **KAPI 0:** yedek restore tatbikatı yeşil (satır sayısı + md5) — *stand-in ✅, üretim ⏳*; Google web girişi Supabase'de etkin — *⏳ Şahin*; README V2 yayında — *✅*; pytest 381 / tsc 0 korunuyor — *✅ (381 + 21 yeni)*.

### FAZ 1 — Kimlik, anket, çok model, web uygulaması (1–1.5 hafta)
- [ ] Router bölme (`routers/*`) — davranış sıfır değişim; 381 yeşil.
- [ ] `core/model_router.py` + env seti; 2.5 fallback'leri kaldır; görsel → `gemini-3.1-flash-image`; `/health` sadeleştir; `model_usage_log`.
- [ ] Kanıt Vision fixture testleri (su≠meyve ≤40, doğru eşleşme ≥60) → **B4 kapanır**.
- [ ] Plan üretimi A/B: `3.1-pro-preview` vs `4-argon` (10 niyet, kör puanlama).
- [ ] `user_surveys` + `/me/survey` + `SurveyGate` + 3 ekran + bellek bloğu + yollar sıralaması.
- [ ] Giriş ekranı iki sekme ("Kendim için"/"Kurumum için"); `auth-screen` bölünür.
- [ ] `app.niyetsen.com`: `npx expo export --platform web` → Hostinger alt alan adı (statik SPA + `.htaccess` fallback); PKCE handler `app.niyetsen.com/auth/callback` (**`niyetsen.com/auth/callback` mobil sayfası kalır**); Supabase redirect kesin yollar; Railway CORS; Google OAuth origins; web'de IAP yok → "Kurumun karşılıyor / mağazadan abone ol" metni.
- [ ] `lib/api.ts` domain bölme; 7 hex → token; `AUTH_DISABLED` varsayılan false.
- [ ] **AAB güvenlik kapanışı (R23, mobil repo):** `android.blockedPermissions` = `RECORD_AUDIO`, `SYSTEM_ALERT_WINDOW`, eski depolama izinleri; `auth-redirect.ts` implicit token dalı kaldırılır (yalnız PKCE `code` / `token_hash`), auth dönüşü `niyetsen://auth/callback` + `state`; R8/shrink açık (Reanimated keep kuralları + cihaz smoke); `ui-tooling` release'ten dışarı; `expo-dev-client` yalnız development profilinde; `allowBackup=false`. Yeni AAB aynı taramadan geçer (`docs/security/AAB_TARAMA_2026-10.md` §9).
- [ ] `tasks.image_url` yeni yazımları göreli anahtar + `StorageGateway.public_url` (R21).
- **KAPI 1:** Web'de Google ile giriş + aynı hesap mobilde; anket 3 soru cihazda; model router birim testleri; Vision fixture yeşil; yeni AAB taramasında YÜKSEK 0; tsc 0; pytest ≥ 420.

### FAZ 2 — Organizasyon çekirdeği (1.5–2 hafta)
- [ ] Migration: `organizations`, `org_departments`, `org_memberships`, `org_invites`, `org_intentions`, `org_intention_links`, `org_audit_log`, `platform_admins`, `feature_flags`, `reward_wallet`, `wallet_ledger`, `integration_outbox`, `storage_objects`; `league_members` FK düzeltmesi.
- [ ] `org_service` + `/org/*` uçları (oluştur, davet, katıl/onay, ayrıl, rol, departman, kurumsal niyet CRUD, niyet-plan bağla).
- [ ] `core/authz.py` rol türetme; `platform_admins` → `app_metadata`.
- [ ] `wallet_service` + `outbox_service` (bayrak kapalı; defter yazımı test edilir).
- [ ] Mobil: `davet.tsx`, `kurumum.tsx`, Profil "Kurumum" chip, "kurumun ne görüyor" sayfası.
- [ ] Rapor "Kurumum" kartı.
- **KAPI 2:** Üye daveti → onay → kurumsal niyete plan bağlama uçtan uca cihazda; `test_privacy_k5.py` iskeleti; wallet defteri puan formülünü etkilemiyor (scoring testleri aynı).

### FAZ 3 — İK paneli + rollup + içgörü (2 hafta)
- [ ] `org_daily_rollups` cron (gece, TZ İstanbul) + geriye dönük doldurma.
- [ ] `org_analytics_service`: k≥5 guard (filtre kombinasyonları dâhil), kural bazlı ayna cümlesi, `ORG_INSIGHT_PROMPT` (yalnız toplu JSON, `gemini-4-argon`).
- [ ] `(org)/` ekranları (§6.3), `react-native-svg` grafikler, CSV dışa aktarım (audit).
- [ ] PostHog org event'leri.
- **KAPI 3:** 2 pilot kurum (biri Şahin'in çevresi), k<5 departman gizleniyor (test + manuel), panel iPad/masaüstü/mobil web'de taşmasız; **Expo vs Next.js kararı burada**.

### FAZ 4 — Platform admin + maliyet görünürlüğü (3–4 gün)
- [ ] `(admin)/` ekranları, `/admin/*` uçları, model maliyet tablosu, bayrak yönetimi, destek araçları.
- **KAPI 4:** Admin dışı kullanıcı `/admin`'e 403; model maliyeti günlük görünüyor.

### FAZ 5 — niyetsen.com yenileme + Hostinger (1 hafta)
- [ ] İlkbahar tasarım (Figma → statik HTML), Bireyler/Kurumlar, Nasıl çalışır, Fiyatlandırma, demo talep (`/public/leads`), blog korunur, 5 dil yasal, Giriş/Panel linkleri.
- [ ] Hostinger yayın (§11 kontrol listesi), DNS apex+www, SSL, header eşlenikleri, sitemap/robots/llms.txt.
- **KAPI 5:** Lighthouse ≥90 (perf/a11y/SEO), tüm eski URL'ler 200 veya 301, formlar API'ye yazıyor.

### FAZ 6 — Kurumsal faturalama + RC deneyleri (1 hafta)
- [ ] RC Web Billing veya fatura akışı; koltuk → `premium` grant/revoke; "Kurumun karşılıyor" rozeti.
- [ ] RC Experiment #1 (paywall varyantı) — Play ürünü canlı olduktan sonra.
- **KAPI 6:** Pilot kurumda koltuk aktif → üyede PRO; koltuk iptal → 24 sa içinde kalkıyor.

### FAZ 7 — Büyük sunucuya geçiş (§7.2) (1 hafta + 14 gün gözlem)
- [ ] Hedef ortam, migration'lar, `StorageGateway` S3, auth stratejisi (K10), çift JWKS penceresi, dondurma gecesi, kontrol toplamları, 14 gün salt okunur Supabase.
- **KAPI 7:** Satır/md5/puan toplamı eşit; 24 sa hata < %1; geri dönüş planı test edildi.

### FAZ 8 — Ödül/entegrasyon pazarı (sonra)
- [ ] `partner_integrations`, `redemptions`, partner API, "Ödüller" sekmesi, outbox yayımcı, ilk 1–2 anlaşmalı partner (kahve/kıyafet), App Review notu.
- **KAPI 8:** Sandbox partnerde kupon uçtan uca; cüzdan harcaması rank'i düşürmüyor.

### Paralel / sürekli
Play IAP + Data Safety (mevcut sprint), Sentry/PostHog, `pytest`/`tsc` yeşil,
Expo Go gerçek cihaz testi, güvenlik raporu YÜKSEK'leri sıralı.

---

## §14. Cursor çalışma düzeni (alt ajanlar, hook'lar, skill'ler)

| Tür | Ad | Görev |
|---|---|---|
| Skill | `niyetsen-kurumsal-pazar` ✅ | Pazar/gizlilik/fiyat hafızası, REA sınırları |
| Agent | `niyetsen-org-mimar` | Org tabloları/servis/uç; k≥5 guard; Repository disiplini |
| Agent | `niyetsen-gizlilik-denetci` | Her org/analytics PR'ında KVKK + k≥5 + utandırmama denetimi; `test_privacy_k5.py` zorunlu |
| Agent | `niyetsen-web-vitrin` | niyetsen.com statik yeniden tasarım, Hostinger yayın, SEO |
| Agent | `niyetsen-model-router` | Model matrisi, fallback, fixture testleri, maliyet logu |
| Hook | `afterFileEdit` (mobil `.tsx`) | hex / RN-Easing / `any` tarayıcı; `tsc` tetik |
| Hook | `beforeShellExecution` | `railway up` yanlış dizin uyarısı; `accept-deploy` **deny** |
| Hook | `beforeSubmitPrompt` | sır deseni (anahtar/JWT) engeli |

Not: Cursor'da görünen "README" alt ajanı aslında `kraken-cli` eklentisinin
`agents/README.md` dosyası (yanlışlıkla ajan sayılıyor); README'yi biz yazarız.

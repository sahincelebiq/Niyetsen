# Niyetsen

> Niyetini söze, sözünü kırılmayan bir zincire çevir.
> Turn your intention into words, and your words into an unbroken chain.

Niyetsen'in bireysel çekirdeği (niyet → görselli plan → foto kanıtı → puan →
zincir) **aynen kalır**; V2 ile üstüne **organizasyon katmanı** gelir:
şirketler / İK / yöneticiler çalışanlarının *toplulaştırılmış ve anonim*
niyet–aktivite verisini görür, **kurumsal niyet** tanımlar, çalışan bu niyeti
kendi planına bağlar. Aynı hesap **mobil + web**'de çalışır; niyetsen.com vitrin
olmaktan çıkıp giriş kapısı + kurumsal anlatı + blog olur.

Niyetsen is a gamified life-assistant: a conversation turns the user's
intention into an illustrated daily plan, tasks are closed with photo proof
(AI vision), a points/penalty/streak engine keeps the chain alive. V2 adds an
organization layer (aggregated, anonymous team insight) on top of the same
individual core; one account works on mobile and web.

**Durum (2026-10-17):** V2 Kurumsal Pivot **onaylandı**; aktif faz **V2 FAZ 0 —
Hazırlık ve zemin**. Play Store çıkış sprinti paralel sürer. Organizasyon
paneli, cüzdan, çok modelli yönlendirme bu README'de **"V2 hedef — Faz X"**
olarak işaretlidir; henüz kodda yoktur.

---

## 1. Nereye bakmalı / Where to start

| İhtiyaç | Dosya |
|---|---|
| **V2 yol haritası (tek gerçek kaynak, Faz 0–8, KAPI'lı)** | [`docs/NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md`](docs/NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md) |
| Kilitli ürün kararları + veri modeli (§1 aynen geçerli; §1.14 V2 kilitleri) | [`NIYETSEN_MASTER_PLAN.md`](NIYETSEN_MASTER_PLAN.md) |
| Ajan çalışma kuralları (Cursor / Claude Code) | [`CLAUDE.md`](CLAUDE.md) · [`AGENTS.md`](AGENTS.md) |
| Mimari (katmanlar, istek akışı) — *2.5 model adları bayat, Faz 1'de güncellenir* | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Neyin nerede olduğu — *sayılar bayat, Faz 1'de güncellenir* | [`docs/REPO_MAP.md`](docs/REPO_MAP.md) |
| Güvenlik duruşu + denetim | [`docs/SECURITY.md`](docs/SECURITY.md) · [`docs/security/`](docs/security/) |
| Yeni geliştirici kurulumu | [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) |
| Backend ayrıntısı (servisler, uçlar, model matrisi, cron, testler) | [`niyetsen-backend/README_BACKEND.md`](niyetsen-backend/README_BACKEND.md) |
| Görev kuyruğu (Play sprinti) | [`docs/SONRAKI_SIRA.md`](docs/SONRAKI_SIRA.md) |
| Play Store hedefi + yatırımcı bug listesi B1–B9 | [`docs/PLAYSTORE_GOAL.md`](docs/PLAYSTORE_GOAL.md) |
| Supabase'e özel bağımlılık envanteri + taşınma karşılıkları (Faz 0) | [`docs/SUPABASE_BAGIMLILIK.md`](docs/SUPABASE_BAGIMLILIK.md) |
| Yedek / geri yükleme tatbikatı / büyük sunucuya geçiş protokolü (Faz 0) | [`docs/GECIS_PROTOKOLU.md`](docs/GECIS_PROTOKOLU.md) |
| Tüm doküman dizini | [`docs/README.md`](docs/README.md) |
| Store görselleri + üretici script'ler | [`store-listing/INDEX.md`](store-listing/INDEX.md) |
| Mobil depo (ayrı git) | [github.com/sahincelebiq/Niyetsen-mobile](https://github.com/sahincelebiq/Niyetsen-mobile) |

Çelişkide sıra: V2 plan §1 → `NIYETSEN_MASTER_PLAN.md` §1 →
`.cursor/rules/niyetsen-hafiza.mdc` → yoksa Şahin'e sor. Uydurma.

---

## 2. İki yüzey mimarisi / Two surfaces, one codebase

```
          ┌──────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
          │  Mobil (iOS + Android)   │   │  Web uygulaması          │   │  Panel (İK / yönetici)   │
          │  SDK 54 · expo-router 6  │   │  app.niyetsen.com        │   │  panel.niyetsen.com      │
          │  RN 0.81.5 · Reanimated 4│   │  AYNI Expo kodu, web     │   │  AYNI bundle, (org)/     │
          │  5 sekme + stack ekranlar│   │  export (statik SPA)     │   │  rota grubu              │
          │  BUGÜN                   │   │  V2 hedef — Faz 1        │   │  V2 hedef — Faz 3        │
          └────────────┬─────────────┘   └────────────┬─────────────┘   └────────────┬─────────────┘
                       │          HTTPS · Bearer JWT (Supabase Auth, JWKS)           │
                       └──────────────────────────────┬──────────────────────────────┘
                                                      ▼
                                   ┌──────────────────────────────────────┐
                                   │  FastAPI  (Railway `api` servisi)    │
                                   │  app/api/routes.py → 61 uç           │
                                   │  services/ (28 modül) · core/        │
                                   │  Repository ABC  ·  StorageGateway*  │
                                   └───────┬──────────────┬───────────────┘
                 Railway `cron` (5 dk)     │              │
                 close-day · bildirim      │              │
                       ┌───────────────────┘              └─────────────────────┐
                       ▼                                                        ▼
   ┌─────────────────────────────────────┐              ┌─────────────────────────────────────┐
   │  BUGÜN: Supabase                    │              │  Gemini API (kapı: gemini_client)   │
   │  Postgres + Auth + Storage          │              │  bugün: gemini-3.1-pro-preview      │
   │  RLS açık, politika yok (backend)   │              │         + 2.5 ailesi fallback       │
   ├─────────────────────────────────────┤              │  V2 Faz 1: görev bazlı model router │
   │  YARIN (Faz 7): standart Postgres   │              │         (V2 plan §5.5 matrisi)      │
   │  + S3-uyumlu depo (MinIO/S3)        │              └─────────────────────────────────────┘
   │  Repository + StorageGateway ile    │              Unsplash (görsel) · RevenueCat (IAP)
   │  sıfır kayıplı geçiş (V2 §7)        │              Sentry · PostHog · Expo Push
   └─────────────────────────────────────┘

   niyetsen.com → statik HTML vitrin + blog + yasal sayfalar, CANLI HOST: Hostinger Business
                 (`website/vercel.json` ve `niyetsen-website.vercel.app` KALINTI — kapatılacak, V2 §11 H6)
   * StorageGateway: V2 hedef — Faz 1–2 (bugün tek doğrudan supabase istemcisi image_service.py:387)
```

- **Backend** — Python 3.11+ / FastAPI. Tüm iş mantığı, oyun motoru, AI
  çağrıları, kanıt doğrulama. Railway'de iki servis: `api` + `cron`.
- **Mobil / Web** — tek Expo Router uygulaması (`mobile/`, **ayrı git deposu**).
  `app.json` → `web.output: static`. Ayrı bir Next.js kullanıcı uygulaması
  yazılmaz; İK paneli aynı kodda `(org)/` rota grubu olarak başlar (Faz 3
  KAPI'sında Next.js'e ayırma kararı o zaman verilir).
- **AI** — Google Gemini, tek geçit `core/gemini_client.py`. Bugün
  `gemini-3.1-pro-preview` (sohbet + plan + Vision) + `gemini-2.5-*` fallback,
  `gemini-2.5-flash-image` (plan görseli, Unsplash hibrit),
  `gemini-embedding-001` (RAG). V2 Faz 1'de `core/model_router.py` görev bazlı
  yönlendirir; 2.5 ailesi fallback'ten çıkar. Model adı uydurulmaz —
  yalnız ai.google.dev/gemini-api/docs/models listesinden.
- **Kimlik** — Supabase Auth (e-posta/şifre + OTP, Google, Apple); backend
  JWT'yi JWKS ile her istekte doğrular (`/health` hariç). Rol **sunucuda**
  türetilir (V2: `org_memberships` + `app_metadata.platform_role`;
  `user_metadata` yetkide asla kullanılmaz).
- **Abonelik** — bireysel: RevenueCat, yalnız IAP. Kurumsal: ödeme uygulama
  dışı, web panelden (V2 hedef — Faz 6).
- **Website** — `website/` saf statik HTML (19 TR blog yazısı, 5 dilde yasal
  sayfa). Canlı host **Hostinger Business**; Vercel yalnız kalıntı.

---

## 3. Depo yapısı / Repository layout

```
Niyetsen/                          ← kök git deposu (backend + docs + website)
├── README.md                      ← buradasın
├── README_BACKEND.md              ← niyetsen-backend/README_BACKEND.md ile birebir kopya
├── NIYETSEN_MASTER_PLAN.md        ← kilitli kararlar §1 (+ §1.14 V2), veri modeli §2
├── CLAUDE.md · AGENTS.md          ← ajan kuralları
├── STORE_READINESS.md             ← mağaza hazırlık listesi
├── docs/                          ← tüm dokümanlar
│   ├── NIYETSEN_V2_KURUMSAL_PIVOT_MASTER_PLAN.md   ← V2 yol haritası (Faz 0–8)
│   ├── ARCHITECTURE.md · REPO_MAP.md · SECURITY.md · DEVELOPER_GUIDE.md
│   ├── SONRAKI_SIRA.md · PLAYSTORE_GOAL.md · FAZ8_LANSMAN.md
│   ├── security/                  ← denetim raporları
│   ├── supabase/                  ← şema durumu
│   └── arsiv-planlama/            ← eski planlama belgeleri + README_v1_2026-10.md
├── niyetsen-backend/              ← Python / FastAPI ("çekirdek beyin")
│   ├── app/{api,core,services,storage,models}/
│   ├── knowledge/                 ← RAG bilgi tabanı (Railway imajına COPY'lenir)
│   ├── supabase/migrations/       ← DDL TEK KAYNAK (29 SQL + RUN_IN_SUPABASE_SQL_EDITOR.sql)
│   ├── scripts/                   ← cron giriş noktası, yedek (pg_dump / verify / tatbikat), ingest, Railway yardımcıları
│   ├── tests/                     ← 43 test dosyası, 381 + yedek testleri
│   └── railway.api.toml · railway.cron.toml · Dockerfile · Dockerfile.cron (pg_dump 17)
├── mobile/                        ← Expo uygulaması — AYRI GİT DEPOSU (Niyetsen-mobile)
│   └── src/app/                   ← expo-router: (tabs)/ 5 sekme + stack ekranlar
├── website/                       ← niyetsen.com statik HTML (Hostinger); .htaccess
├── store-listing/                 ← Play / App Store görselleri + üretici script'ler
└── .cursor/                       ← rules/ (hafıza, sprint) · skills/ · agents/ (org-mimar, gizlilik-denetci,
                                     web-vitrin, model-router) · hooks.json + hooks/ (hex/Easing/any, railway, sır)
```

Mobil tab'lar (`mobile/src/app/(tabs)/`): `index` Sohbet · `daily` Bugün ·
`explore` Planım · `rank` Zincir · `settings` Profil. Mistik, rapor, paywall,
yollar, lig vb. kök Stack'te. V2 hedef (Faz 1–3): `auth` iki sekme, anket
adımı, `kurumum`, `davet`, `(org)/`, `(admin)/`.

---

## 4. Kurulum ve çalıştırma / Setup

**Backend**
```bash
cd niyetsen-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # GEMINI_API_KEY vb. .env'e — KODA DEĞİL
pytest -q                       # 381 geçmeli (anahtar gerekmez, in-memory repo)
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```
Dev'de kimlik `AUTH_DISABLED=true` + `X-User-Id: <id>` başlığı. Fiziksel
cihaz için `--host 0.0.0.0` ve mobil `.env`'de Mac LAN IP'si.

**Mobil (Expo)**
```bash
cd mobile
npm install
cp .env.example .env            # EXPO_PUBLIC_* — yalnız publishable/anon anahtarlar
npx expo start                  # i / a / Expo Go QR
npx tsc --noEmit                # 0 hata şartı
```
RevenueCat satın alma Expo Go'da çalışmaz (EAS / dev build gerekir).

**Web uygulaması (V2 hedef — Faz 1)**
```bash
cd mobile
npx expo export --platform web  # dist/ → app.niyetsen.com (Hostinger alt alan adı, statik SPA)
```
`.htaccess` SPA fallback, PKCE handler `app.niyetsen.com/auth/callback`,
Railway `CORS_ALLOWED_ORIGINS`'e `app.` + `panel.` eklenir. `niyetsen.com/auth/callback`
mobil şifre sıfırlama bilgi sayfası olarak **kalır**.

**Website (niyetsen.com)**
Statik HTML; yayın paketi **allowlist** ile üretilir ve yalnız o yüklenir:
```bash
cd website && scripts/build_release.sh   # → website/_release/ (vercel.json, .py, .env*, .vercel/ dışarıda)
```
Deploy = Hostinger Business (hPanel / Hostinger MCP `hosting_deployStaticWebsite`,
canlıyı ezer → Şahin onayı; ardından önbellek temizliği). `website/.htaccess`:
header'lar, HSTS, clean-URL fallback, `txt|xml` 1 saat cache, `404.html`
(V2 §11 H1–H5). Vercel kalıntısının kapatılması (H6) Şahin panel işi.

Tam kurulum, ortam değişkenleri ve sık sorunlar: [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md).

---

## 5. Test ve kalite kapıları / Quality gates

| Kapı | Şart |
|---|---|
| Backend | `pytest -q` → **381 geçti** (2026-10-17). Düşürme; V2 fazları artırır (Faz 1 KAPI ≥ 400). |
| Mobil tip | `npx tsc --noEmit` → **0 hata** |
| Reanimated | `Easing` / `Animated` **asla** `react-native`'ten import edilmez (worklet crash). ESLint `no-restricted-imports` kuralı kaldırılamaz. |
| Tema | Hex hardcode yok — yalnız `theme.ts` / `MysticColors` token'ları (bugün 7 istisna kamera siyah/beyaz, Faz 1'de token). |
| TypeScript | `any` yok (bugün 0). |
| Gizlilik (V2) | Her org/rollup ucu için `test_privacy_k5.py` zorunlu (Faz 2+). |
| Cihaz | Her ekran gerçek cihazda (Expo Go / dev build); simülatör yetmez. |

**Commit biçimi:** kök `v2: <konu>` · mobil `v2-ui: <konu>`; küçük, tek konulu.
**Commit ve push yalnız Şahin isteyince.** `mobile/` ayrı depodur, kök repoya
commit edilmez.

---

## 6. Deploy

**Railway (backend)** — GitHub push canlıda deploy **tetiklemez**; CLI ile:

```bash
# api: REPO KÖKÜNDEN (rootDirectory = niyetsen-backend; içeriden çalıştırılırsa yol ikiye katlanır)
railway up --project <id> --environment <id> --service api --ci

# cron: niyetsen-backend/ İÇİNDEN (Config-as-code /railway.cron.toml orada)
cd niyetsen-backend && railway up --service cron --ci
```
Doğrulama: `/health` 200 · yeni uçlar JWT'siz 401 · cron log `exit 0`.
Cron servisi `railway.cron.toml` kullanır (`railway.toml` değil); yanlış
dosya uvicorn açar → 5 dk'da SIGKILL → "Deploy Crashed" spam. Production'da
bekleyen staged patch'e **`accept-deploy` ASLA** (env'leri siler) —
dashboard'dan discard. Tanı: [`docs/RAILWAY_SORUN_GIDERME.md`](docs/RAILWAY_SORUN_GIDERME.md).

**Supabase (migration disiplini)**
- DDL **yalnız** `niyetsen-backend/supabase/migrations/` altında, zaman damgalı,
  standart Postgres (Supabase'e özel RPC / Edge Function / `auth.users` FK'si
  yeni tablolarda yok).
- SQL Editor'da **yalnız VERIFY** (`RUN_IN_SUPABASE_SQL_EDITOR.sql`); elle DDL
  yapıştırma biter. Migration'lar otomatik uygulanmaz — Şahin çalıştırır.
- Kök `supabase/migrations/` stub'ı Faz 0'da kaldırıldı (tek kaynak).
- `plans.id` ve `users.id` **TEXT** — FK yazarken `text references`.
- Supabase'e özel her bağımlılığın taşınma karşılığı:
  [`docs/SUPABASE_BAGIMLILIK.md`](docs/SUPABASE_BAGIMLILIK.md).

**Yedek ve geçiş (V2 §7 — Faz 0)**
- Günlük `pg_dump --format=custom` (şemalar `public,auth,storage`) → S3-uyumlu
  kova (R2/B2/MinIO), 30 gün saklama: `scripts/backup_pg_dump.py` (+
  `backup_io.py`, saf mantık `app/core/backup.py`, testler `tests/test_backup.py`).
  Cron turuna bağlı (`run_scheduled_jobs.py` → `backup` adımı, `BACKUP_HOUR_UTC`);
  cron imajı `Dockerfile.cron` (postgresql-client-17 — Supabase 17.6).
- `scripts/verify_backup.py` (snapshot / compare / fetch-latest / local-dump /
  drill) + `scripts/restore_drill_local.sh`: geçici PG17'ye restore + satır
  sayısı / md5 karşılaştırması; haftalık tatbikat tek komut.
  `scripts/local_pg_from_migrations.sh`: gerçek migration'lar vanilla Postgres'te
  (29/29 hatasız, 2026-10-17). **KAPI 0** = üretim dump'ıyla tatbikat yeşil
  (boru hattı stand-in ile doğrulandı; üretim koşusu DB şifresi + kova bekliyor).
- Geçiş günü protokolü (dondurma penceresi, kontrol toplamları, çift JWKS,
  14 gün salt okunur Supabase) ve tatbikat kayıtları:
  [`docs/GECIS_PROTOKOLU.md`](docs/GECIS_PROTOKOLU.md).

**Mobil** — EAS (`mobile/eas.json`); Play / TestFlight profilleri `package.json` script'lerinde.

---

## 7. Gizlilik tabanı / Privacy floor (V2 kilit 1.2/1 — tartışılmaz)

- **k ≥ 5 toplulaştırma:** 5 kişiden az departman / filtre kombinasyonu için
  veri **döndürülmez** — servis katmanında (`org_analytics_service`), SQL
  view'da değil. Kesişen filtreler dâhil.
- **Yönetici tek kişiyi görmez:** İK / yönetici hiçbir ekranda bir kişinin
  görev, plan, sohbet, fal veya anket "eksik yön" cevabını görmez. Görünen:
  katılım %, 6 kategori dağılımı, zincir ortalaması, kurumsal niyete bağlı
  ilerleme %, anket toplamları.
- **Davet + açık onay:** katılım geri alınabilir; katılmayan hiçbir ürün içi
  dezavantaj yaşamaz. Bireysel veri işleme dayanağı **kullanıcı sözleşmesi**,
  işveren değil; organizasyon verisi yalnız toplulaştırılmış işlenir.
- **Fal / mistik / kriz verisi organizasyona asla akmaz.**
- **Roller:** `owner` / `hr_admin` / `manager` / `member`; her panel okuması
  `org_audit_log`'a yazılır.
- **Utandırma yasağı panelde de:** "en az aktif çalışan" listesi yok; yalnız
  kazanım dili. Her panel ekranında sabit not: "Veriler toplulaştırılmıştır;
  5 kişiden küçük gruplar gösterilmez."
- **Oyun puanı ≠ cüzdan:** `points` ile `reward_wallet` ayrı defterler; puan
  harcanınca rank düşmez (V2 hedef — Faz 2 çekirdek, Faz 8 partner).

Organizasyon katmanı, panel ve cüzdan **V2 hedef — Faz 2–3**; bugün kodda yok.

---

## 8. Oyun kuralları / Game rules (değişmez)

```
Görev tamamlama        +50  (etiketli her kategoriye)
Sessiz kaçırma         −25 × 2ⁿ, TAVAN 200; herhangi bir tamamlama sayacı sıfırlar
Mazeret yolu           sabit −25, katlanmaz, sayaç sıfırlanır; 10. mazerette puan ×0.5
Puan tabanı            0 — negatif yok
Zincir                 günde ≥1 görev = devam; gün sınırı kullanıcı TZ 23:59
Zincir Koruma Jetonu   ayda 1, otomatik
Kanıt                  Vision güven ≥60 onay; <60 nazik tekrar (maks 3, 3.'de beyanla kabul)
6 kategori             İrade · İstikrar · Disiplin · Özgüven · Sosyallik · Özsaygı
Ton                    dürüst yüzleşme evet, utandırma hayır — Wrapped ve panelde kaçırılanlar gösterilmez
```
Kaynak: `niyetsen-backend/app/config.py` sabitleri + `tests/test_scoring.py`
sözleşmesi + `NIYETSEN_MASTER_PLAN.md` §1.2–1.5. Kurumsal katman formülü
değiştirmez.

---

## 9. Yol haritası / Roadmap (V2 §13)

KAPI geçmeden sonraki faza başlanmaz. Aktif: **FAZ 0** (2026-10-17).

| Faz | Özet | KAPI |
|---|---|---|
| **0 — Hazırlık ve zemin** (aktif) | README V2, Supabase leaked-password + sağlayıcı doğrulama, migration tek kaynak, günlük `pg_dump` + `verify_backup.py`, Cursor alt ajan + hook'lar, AAB güvenlik taraması, Hostinger P1 | Yedek restore tatbikatı yeşil; Google web girişi etkin; README yayında; pytest 381 / tsc 0 |
| 1 — Kimlik, anket, çok model, web uygulaması | Router bölme, `model_router.py`, Vision fixture (B4), plan A/B, 3 soru anketi, iki sekmeli giriş, `app.niyetsen.com` | Web'de Google girişi + aynı hesap mobilde; Vision fixture yeşil; pytest ≥ 400 |
| 2 — Organizasyon çekirdeği | Org tabloları, `/org/*`, `authz.py`, wallet + outbox (bayrak kapalı), `davet` / `kurumum` ekranları | Davet → onay → niyet–plan bağlama uçtan uca; `test_privacy_k5.py` iskeleti |
| 3 — İK paneli + rollup + içgörü | `org_daily_rollups` cron, k≥5 guard, `(org)/` ekranları, CSV | 2 pilot kurum; k<5 gizleniyor; Expo vs Next.js kararı |
| 4 — Platform admin + maliyet | `(admin)/`, `/admin/*`, `model_usage_log`, bayraklar | Admin dışı 403; model maliyeti günlük görünür |
| 5 — niyetsen.com yenileme | İlkbahar tasarım, Bireyler / Kurumlar, `/public/leads`, Hostinger yayın | Lighthouse ≥ 90; eski URL'ler 200/301 |
| 6 — Kurumsal faturalama + RC deneyleri | Web Billing veya fatura; koltuk → `premium` grant/revoke | Koltuk aktif → PRO; iptal → 24 sa içinde kalkar |
| 7 — Büyük sunucuya geçiş | Standart Postgres + S3, `StorageGateway`, çift JWKS, dondurma gecesi | Satır/md5/puan toplamı eşit; 24 sa hata < %1 |
| 8 — Ödül / entegrasyon pazarı | `partner_integrations`, `redemptions`, "Ödüller" sekmesi | Sandbox partnerde kupon uçtan uca; cüzdan rank'i düşürmüyor |

**Paralel:** Play IAP + Data Safety sprinti (`docs/PLAYSTORE_GOAL.md`,
B1–B9 kapanmadan "hazır" denmez), Sentry / PostHog, `pytest` / `tsc` yeşil.
Lig: opt-in rumuzlu haftalık gelişim ligi kodda var (`/league/*`); public
leaderboard, bölgesel lig ve Realtime **yapılmaz**.

---

## 10. Güvenlik özeti / Security (özet)

- Sırlar **yalnız** `.env` / Railway / EAS değişkenlerinde; repoda sır yok;
  `.env.example` placeholder taşır.
- Prod kilitleri (`app/main.py`): `AUTH_DISABLED=true`, `USE_SUPABASE_DB=false`,
  boş `CRON_SECRET`, boş `REVENUECAT_WEBHOOK_SECRET` → süreç açılmaz.
- Supabase JWT (JWKS, RS256/ES256, `aud=authenticated`) her istekte; `/health` hariç.
- Rate limit (kullanıcı başına), istek gövdesi tavanı, güvenlik başlıkları,
  güvenli hata yanıtı; foto ≤ 5 MB jpeg/png, yalnız uygulama içi kamera.
- Prompt sırası SYSTEM → CONTEXT → USER tek yerde (`core/prompt_builder.py`);
  kullanıcı mesajı system rolüne karışmaz; araç listesi `core/tools.py` kapalı.
- V2: `/health` yalnız `ok` + `version` döner (Faz 1); `service_role` /
  `sb_secret` web bundle'ında yok (CI grep); servislerde `supabase` import'u
  yasak (CI grep, Faz 1).

Ayrıntı: [`docs/SECURITY.md`](docs/SECURITY.md) · [`docs/security/`](docs/security/).

---

<sub>© Niyetsen — Veri sorumlusu / Data controller: Şahin Çelebi · ai@niyetsen.com</sub>

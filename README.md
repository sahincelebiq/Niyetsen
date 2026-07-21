# Niyetsen

> **Niyetini söze, sözünü kırılmayan bir zincire çevir. 🌙**
> Turn your intention into words, and your words into an unbroken chain.

Niyetsen, kullanıcının "bu yıl nasıl bir hayat istiyorum?" niyetini sohbetle
alıp **görselli, günlük, oyunlaştırılmış bir plana** çeviren; görevleri **foto
kanıtıyla** yaptıran, yapılmayınca puan düşüren; fal & astroloji modülleriyle
zenginleştirilmiş bir yaşam asistanı uygulamasıdır. iOS + Android.

Niyetsen is a gamified life-assistant app. It takes a user's intention through a
conversation, turns it into an **illustrated daily plan**, drives task
completion via **photo proof** (AI vision verification), applies a
points/penalty/streak engine, and adds fortune & astrology modules. iOS +
Android.

---

## 🧭 Bu depoda nereye bakmalı? / Where to start

| İhtiyaç / Need | Dosya / File |
|---|---|
| **Yeni geliştirici — kurulum** / New developer setup | [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) |
| **Mimari** / Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **Neyin nerede olduğu** / Repository map | [`docs/REPO_MAP.md`](docs/REPO_MAP.md) |
| **Güvenlik** / Security overview & audit | [`docs/SECURITY.md`](docs/SECURITY.md) |
| **Ürün yol haritası** / Product roadmap (single source of truth) | [`NIYETSEN_MASTER_PLAN.md`](NIYETSEN_MASTER_PLAN.md) |
| **Tüm doküman dizini** / Full docs index | [`docs/README.md`](docs/README.md) |

---

## 🏗️ Mimari özet / Architecture at a glance

```
┌─────────────────────┐        HTTPS / JWT (Supabase)        ┌──────────────────────┐
│   Mobile (Expo)     │  ───────────────────────────────▶   │  Backend (FastAPI)   │
│  React Native + TS  │                                      │   Python 3.11+       │
│  expo-router        │  ◀───────────────────────────────   │   "çekirdek beyin"   │
└─────────────────────┘         JSON API (42 uç)             └──────────┬───────────┘
         │                                                              │
         │ RevenueCat (IAP)                                             │
         ▼                                              ┌───────────────┼───────────────┐
   App Store / Play                                     ▼               ▼               ▼
                                              ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
                                              │  Supabase    │  │  Gemini API │  │  Unsplash    │
                                              │ Postgres+Auth│  │ 2.5-flash   │  │  (görseller) │
                                              │  +Storage    │  │ (multimodal)│  └──────────────┘
                                              └──────────────┘  └─────────────┘
                                                     ▲
                                              Railway cron (5 dk / 5 min)
```

- **Backend** — Python / FastAPI. Tüm iş mantığı, oyun motoru, AI çağrıları ve
  kanıt doğrulama burada. Railway'de iki servis: API + cron.
- **Mobile** — Expo (React Native + TypeScript, expo-router). *Ayrı bir git
  deposu* (`mobile/.git`).
- **AI** — Google Gemini, 4 ayrı model rol için:
  `gemini-2.5-flash` (sohbet, niyet toplama, fal, foto kanıt doğrulama/vision),
  `gemini-2.5-pro` (plan üretimi — daha güçlü akıl yürütme gerektirir),
  `gemini-2.5-flash-image` — "**Nano Banana**" (plan görseli üretimi, Unsplash ile hibrit),
  `gemini-embedding-001` (RAG embedding).
- **DB / Auth / Storage** — Supabase (Postgres + Auth + Storage).
- **Abonelik / Subscriptions** — RevenueCat (yalnız uygulama içi satın alma / IAP only).
- **Gözlemlenebilirlik** — Sentry (hata), PostHog (analitik).

---

## 📦 Depo yapısı / Repository layout

```
Niyetsen/
├── README.md                  ← buradasın / you are here
├── NIYETSEN_MASTER_PLAN.md    ← tek gerçek kaynak: fazlar, kilitli kararlar, veri modeli
├── CLAUDE.md / AGENTS.md      ← AI ajan çalışma kuralları (Cursor + Claude Code)
├── STORE_READINESS.md         ← App Store / Play yayın hazırlık listesi
├── docs/                      ← TÜM dokümanlar (bu PR ile derli toplandı)
│   ├── README.md              ← doküman dizini
│   ├── ARCHITECTURE.md        ← mimari
│   ├── REPO_MAP.md            ← neyin nerede olduğu
│   ├── SECURITY.md            ← güvenlik + denetim
│   ├── DEVELOPER_GUIDE.md     ← kurulum & çalıştırma
│   ├── FAZ*.md / *_SYNC.md    ← faz geçmişi ve ajan devir notları
│   └── arsiv-planlama/        ← eski .docx/.xlsx planlama belgeleri (arşiv)
├── niyetsen-backend/          ← Python/FastAPI backend ("ana beyin")
├── mobile/                    ← Expo uygulaması (ayrı git deposu)
└── website/                   ← tanıtım sitesi + blog (statik)
```

> Ayrıntılı harita için / For the full map: [`docs/REPO_MAP.md`](docs/REPO_MAP.md).

---

## ⚡ Hızlı başlangıç / Quick start

**Backend:**
```bash
cd niyetsen-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # GEMINI_API_KEY'i .env'e yaz — KODA DEĞİL
pytest -q                    # testler (anahtar gerekmez)
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

**Mobile:**
```bash
cd mobile
npm install
cp .env.example .env         # EXPO_PUBLIC_API_URL vb. doldur
npx expo start
```

> Tam kurulum, ortam değişkenleri ve cihazda test için:
> **[`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md)**.

---

## 🔐 Güvenlik / Security (özet)

- Sırlar **yalnız** `.env` içinde; `.env` gitignore'da; repoda takip edilen sır **yok**.
- Prod'da kimlik doğrulaması kapatılamaz (`app/main.py` çalıştırma-anı kilidi).
- Supabase JWT (JWKS / RS256) her istekte doğrulanır (`/health` hariç).
- Rate limit, istek gövdesi tavanı, güvenlik başlıkları ve güvenli hata yanıtı aktif.

Ayrıntılı denetim: **[`docs/SECURITY.md`](docs/SECURITY.md)**.

---

## 📱 Durum / Status

Aktif geliştirme — mağaza yayını hazırlığı (bkz. [`STORE_READINESS.md`](STORE_READINESS.md)).
Güncel faz ve kilitli kararlar için tek kaynak: [`NIYETSEN_MASTER_PLAN.md`](NIYETSEN_MASTER_PLAN.md).

---

<sub>© Niyetsen — Veri sorumlusu / Data controller: Şahin Çelebi · ai@niyetsen.com</sub>

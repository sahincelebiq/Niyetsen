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

## 🎯 Ürünün üç katmanı / What the product actually is

Niyetsen üç katmandan oluşur; ilki bağı kurar, diğer ikisi değeri derinleştirir.

### 1. AI Asistan — potansiyeli açan sohbet · **ücretsiz, sınırsız**
Rehber genel tavsiye vermez: her istekte **kullanıcı belleği** (aktif niyet,
zincir, rank, son görevler, ruh hali) ve **RAG bilgi tabanı** (felsefe,
motivasyon, atomik alışkanlıklar, 16 gerçek kullanıcı senaryosu) bağlama girer.
Sohbet oturumları başlıklarıyla saklanır; kullanıcı istediği konuşmaya döner.
Ücretsiz katmanda sınırsızdır — **bağ kurulmadan abonelik istenmez** (edinim
ve retention stratejisinin merkezi).

### 2. Plan & Kanıt — çekirdek halka · **premium**
Sohbetten çıkan niyet, kullanıcının gerçek hayatından türeyen 365 günlük
görselli plana dönüşür. Tempo bilinçlidir: ilk günler garantili kazanım,
haftada bir nefes günü, kademeli zorluk, görevlerin birbirine zincirlenmesi.
Her görev uygulama içi kamerayla çekilen tek fotoğrafla kapanır; Vision modeli
değerlendirir, puan işlenir. Ceza caydırır ama **utandırmaz**: tavanlı ceza,
sıfır tabanı, dürüst mazeret yolu, aylık zincir koruma jetonu.

### 3. Mistik Katman — tutundurma kancası · **premium**
Günlük tarot (78 kartlık tam deste), kahve & el falı görsel yorumu,
günlük/haftalık burç. İlke: **fal kader değil, aynadır** — her yorum kullanıcının
niyetine ve bugün atabileceği en küçük adıma bağlanır; korku satılmaz, kriz
sinyalinde yorum durur, her ekranda "eğlence amaçlıdır" ibaresi bulunur.
Ana konumlama yaşam planlamadır; mistik katman ikincil ve ayrıştırıcıdır.

### ✦ İdol Modu — Felsefe Yolları · **premium, ürünün imzası**
> Bu özellik bir film izlenirken doğdu. Film biter, içinde bir şey kıpırdar:
> "Ben de böyle biri olmak istiyorum." O his ~48 saatte söner. Niyetsen o anı
> yakalayıp 365 günlük bir yola çevirir.

Kullanıcı ilham aldığı kişiyi söyler; sistem bunu bir **Felsefe Yolu**'na
çevirir (Greenlights Yolu, Kaizen Yolu, Stoacı Yol, Ustalık Yolu, Şafak Yolu…).
Her yol iki katmanlıdır: **felsefe** (dünya görüşü → rehberin tonuna işler) ve
**pratik** (spor, okuma, rutin, karar biçimi → plan motoruna işler).
İlke: **taklit değil, tercüme** — o kişi olmak değil, disiplinini kullanıcının
kendi hayatının diline çevirmek.

*Hukuki çerçeve kodda zorlanır:* paketler kişi adıyla değil felsefe adıyla
sunulur; kişi adı yalnız "…kamuya açık yaklaşımından ilham alır; kendisiyle
bağlantılı değildir" kaynak notunda geçer (kişilik hakları + App Store 5.2.1).

**Persona veri akışı:** `knowledge/personas/<slug>.json` (15 alanlı dossier:
core_beliefs, mindset, habits, daily_routine, reading_profile,
books_read_or_recommended, decision_style, failure_and_recovery,
public_quotes, lessons_for_users, sources …) → `python -m scripts.ingest_personas`
→ Supabase `idol_personas` + 80-150 kelimelik `persona_chunks`.
**Yeni idol eklemek deploy gerektirmez.** Şema: `knowledge/personas/_SEMA.md`.

---

## 🔄 Çalışma mantığı / Request algorithm

```
Kullanıcı mesajı
  ↓ [1] Rıza + güvenlik kapısı (KVKK onayları, kriz sinyali taraması)
  ↓ [2] Bağlam kurulumu — sıra DEĞİŞMEZ
        SYSTEM  : sabit rehber kimliği (core/prompts.py)
        CONTEXT : RAG parçaları (felsefe · motivasyon · senaryolar ·
                  tetiklenirse tarot/burç/persona) + KULLANICI BELLEĞİ
        USER    : kullanıcı mesajı            ← RAG etiketli, injection korumalı
  ↓ [3] Model çağrısı → yapısal JSON (reply, suggestions, collected, ready)
  ↓ [4] Niyet tamamlandıysa → Plan motoru (Pro model)
        tempo kuralları + (varsa) Felsefe Yolu dossier bağlamı + görseller
  ↓ [5] Günlük döngü: görev → foto kanıtı → Vision skoru → puan + zincir
        gün sonu cron (kullanıcı saat diliminde 23:59) → ceza/koruma/streak
```

**Oyun mekaniği:** görev +50 · sessiz kaçırma −25×2ⁿ (tavan 200) · dürüst
mazeret sabit −25 · puan tabanı 0 · 6 kategori (İrade, İstikrar, Disiplin,
Özgüven, Sosyallik, Özsaygı) · ayda 1 zincir koruma jetonu.

---

## 🗄️ Depolama / Storage map

| Katman | Teknoloji | İçerik |
|---|---|---|
| Veritabanı | Supabase (Postgres) | users, plans, tasks, proofs, points, point_log, streaks, **chat_threads**, chat_msgs, intents, user_consents, push_tokens, bonus_offers, **fortune_log**, **idol_personas + persona_chunks** |
| Kimlik | Supabase Auth (JWT) | e-posta/şifre, Apple & Google |
| Dosya | Supabase Storage | kanıt fotoğrafları (özel bucket), plan görselleri (açık) |
| Bilgi tabanı | `knowledge/` + `rag_service` | felsefe, motivasyon, atomik alışkanlıklar, senaryolar, tarot (78 kart), burçlar, persona dossier'ları |
| Vektör | Gemini embedding + kosinüs + **disk önbelleği** | yeniden başlatmada embedding maliyeti tekrarlanmaz |
| Ödeme | RevenueCat (yalnız IAP) | 7 gün deneme → aylık/yıllık abonelik |

---

## 📱 Durum / Status

Aktif geliştirme — mağaza yayını hazırlığı (bkz. [`STORE_READINESS.md`](STORE_READINESS.md)).
Faz 7 (v2) kod tarafı tamamlandı: fal modülü, RAG, sohbet oturumları, İdol Modu
ve store güvenlik altyapısı devrede; **168 otomatik backend testi yeşil**.
Güncel faz ve kilitli kararlar için tek kaynak: [`NIYETSEN_MASTER_PLAN.md`](NIYETSEN_MASTER_PLAN.md).

---

<sub>© Niyetsen — Veri sorumlusu / Data controller: Şahin Çelebi · ai@niyetsen.com</sub>

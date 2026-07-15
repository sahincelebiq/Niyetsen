# FAZ 5 — Paywall, UX & Entegrasyon (aktif plan)

> **Cursor sağ panel — tek açık görünüm.** Eski başlıklar (KVKK/KAPI 3/FAZ 4 Build Locally)
> **kapatıldı**; bu dosya güncel kaynak. Arşiv: `NIYETSEN_MASTER_PLAN.md` §3.

## ✅ Kapalı kapılar (geri açma)

| KAPI | Kapanış | Kanıt |
|------|---------|-------|
| **KAPI 3** — görev/kanıt/puan/zincir | **2026-07-15** | Gerçek cihaz foto→puan→rank; Supabase smoke test; `close_due_users` 56 kullanıcı 0 hata; backend **127 test** |
| **KAPI 4** — bildirim + guardrail + KVKK | **2026-07-14** | Push cihazda; kriz filtresi; consent API; bonus hub testleri |
| **FAZ 4** | **Kapandı** | Yukarıdaki KAPI 4 ile birlikte |

### KAPI 3 kapanış özeti (elle + otomatik)

- [x] `POST /task/{id}/proof` → Storage + Gemini Vision ≥60
- [x] Puan kuralları §1.2 (`scoring_service` + testler)
- [x] Mazeret + sessiz kaçırma + zincir (`task_lifecycle_service`)
- [x] Rank ekranı backend `overall_rank` wired
- [x] Supabase prod round-trip (`scripts/smoke_test_supabase`)
- [x] Railway cron **direct mod** kodu hazır (`run_scheduled_jobs.py`, exit 0)
- [x] Gerçek cihaz / Expo Go + Supabase JWT auth

> **Cron ops:** Railway deploy/config ince ayarı Fable 5 oturumuna ertelendi — **KAPI 3'ü bloklamaz**; oyun mantığı prod Supabase'te doğrulandı.

---

## ⏸ FAZ 5 — Mağaza hesapları bekleniyor

**Devam anahtarı:** `CANLI YA DEVAM APP`

**Şu an:** Expo Go + lokal ağ → UX/QC/mockup + Instagram içerik.

### Aktif mobil branch

```
fix/ux-consent-optimizasyon  (origin ile senkron)
```

**Korunacak UX düzeltmeleri (geri alma):**

1. `kvkk_explicit_consent` → `privacy` onayına bağlı (`consent-gate`, `onboarding`) — backend sözleşmesi
2. Tab bar sistem teması (`app-tabs.tsx` / `.web.tsx`) — sabit renk yok
3. `index.tsx` akıllı scroll (`nearBottomRef`) + `ChatComposer` `sending` prop
4. `explore.tsx` gereksiz `listProjects` yok; hero plan adına düşer
5. `daily.tsx` kamera → İrade Modu yan etkisi yok
6. `settings.tsx` İrade Modu anında kayıt (`changeIradeMode`)
7. `project-sheets.tsx` rename Enter/Vazgeç + paywall Alert

### Mobil güvenlik (yeni)

- Yalnızca `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — `service_role` mobilde **yasak**
- `npm run verify-env` ile kontrol

---

## 🔗 Tam entegrasyon durumu

| Katman | Durum | Not |
|--------|-------|-----|
| **Backend ↔ Supabase** | ✅ | `USE_SUPABASE_DB=true`, smoke test OK |
| **Mobil ↔ Supabase Auth** | ✅ | publishable key + JWT |
| **Mobil ↔ Backend API** | ✅ | Bearer token; lokal `192.168.x:8000` veya Railway prod |
| **Railway API prod** | ✅ | `/health` 200 |
| **Railway Cron** | ⚠️ | Direct kod hazır; dashboard config path + pause/resume scriptleri |
| **Cursor Railway MCP** | ⚠️ | CLI yok → remote MCP veya `brew install railway` |
| **RevenueCat / IAP** | ⏸ | Kod hazır; sandbox E2E mağaza hesabı sonrası |
| **PostHog / Sentry** | 🔧 | İskelet; key'ler opsiyonel |

---

## Lokal geliştirme (Expo Go)

```bash
# Terminal 1
cd niyetsen-backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
cd mobile
# .env → EXPO_PUBLIC_API_URL=http://$(ipconfig getifaddr en0):8000
npx expo start -c --lan
```

---

## KAPI 5 kapanış (hesap açılınca)

Sandbox satın alma → webhook/sync → `active` → kilitler açılır → Geri Yükle → iptal.

Detay: `docs/KAPI5_REVENUECAT_SETUP.md` · `STORE_READINESS.md`

- [x] Backend trial + paywall + webhook + sync
- [x] Mobil paywall + RevenueCat SDK + polling
- [ ] Apple ($99) + Google ($25)
- [ ] Sandbox IAP E2E cihaz

---

## Manus AI ile çalışma

- **Cursor (burası):** kod, backend, Railway, Supabase, test
- **Manus AI:** araştırma, içerik, Instagram Reels, store metinleri
- **Ortak köprü:** `docs/AGENT_HANDOFF.md` + GitHub + (opsiyonel) Manus MCP
- Kurulum: `docs/MANUS_CURSOR_SYNC.md`

---

### Cron hâlâ kırmızı / mail geliyor

1. **Hemen mail kes:** `python -m scripts.pause_railway_cron` + commit/push `railway.cron.toml`
2. **Kök sebep:** cron servisi `railway.toml` (uvicorn) kullanıyorsa → Config-as-code **`/railway.cron.toml`**
3. **Doğru log:** `cron modu: direct` — yanlış: `POST /cron/close-day`

---

## Sıradaki işler (mağaza öncesi)

1. UX branch QC (consent, tab bar dark, chat scroll, settings irade)
2. Instagram Reels / tanıtım içeriği (Manus)
3. Ekran görüntüleri + store mockup
4. Cron Railway ince ayarı (Fable 5) — mail spam kesildi, oyun mantığı OK

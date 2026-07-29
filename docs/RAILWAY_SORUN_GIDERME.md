# Railway "Deploy Crashed" — Tanı Karar Ağacı (FAZ 8)

> Kullanım: Railway → servis → **Deployments → View Logs**. Logdaki desene
> göre aşağıdan ilerle. İki ayrı servis var: **web** (railway.toml, uvicorn)
> ve **cron** (railway.cron.toml, 5 dk'da bir). Hangisinin çöktüğüne
> Deployments sekmesinden bak — çoğu "çöküyor" şikâyeti CRON servisinden gelir.

## 0. Hangi servis çöküyor?

- Mail/panel "Deploy Crashed" hangi servis adını gösteriyor? Web mi cron mu?
- Cron çöküyorsa → Bölüm A. Web çöküyorsa → Bölüm B.

## A. Cron servisi çöküyor

`scripts/run_scheduled_jobs.py` ASLA nonzero exit vermez (kod garantisi).
Cron yine de çöküyorsa tek olası neden: **cron servisi yanlış config ile
build oluyor** — railway.cron.toml yerine railway.toml kullanıyor ve uvicorn
başlatıyor; 5 dk sınırında SIGKILL yiyip "crashed" görünüyor.

1. Logda `POST /cron/close-day` veya `Uvicorn running` görüyorsan → TANI KESİN:
   Railway dashboard → cron servisi → **Settings → Config-as-code** alanına
   `/railway.cron.toml` yaz → redeploy.
2. Doğru log deseni şu üçlüdür: `cron modu: direct` → `close-day: {...}` →
   `cron tamamlandı (exit 0)`.
3. `cron env eksik — iş atlandı` görüyorsan: cron servisinin Variables'ında
   `USE_SUPABASE_DB=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (veya
   `SUPABASE_SECRET_KEY`) eksik → web servisinden kopyala
   (`python -m scripts.sync_cron_railway_env` yardımcısı var).

## B. Web servisi çöküyor

Logda `boot: env=...` satırını ara (main.py'nin ilk işi — 2026-07-29'da eklendi).

1. **`boot:` satırı YOK + `RuntimeError: ENV=prod iken ...`** → bilinçli
   güvenlik kilidi. Mesaj hangi env eksikse onu söyler: `AUTH_DISABLED=false`,
   `USE_SUPABASE_DB=true`, `CRON_SECRET`, `REVENUECAT_WEBHOOK_SECRET`.
   Railway Variables'a ekle → redeploy. (Kilidi GEVŞETME — store güvenliği.)
2. **`boot:` satırı YOK + supabase/create_client hatası** → `SUPABASE_URL`
   veya service key boş/bozuk (repo import anında bağlanır). Variables kontrol.
3. **`boot:` satırı VAR, sonra traceback** → gerçek kod hatası; traceback'i
   Cursor'a yapıştır (Sentry'de de görünür, SENTRY_DSN setliyse).
4. **`boot:` VAR, log temiz ama healthcheck fail** → `/health` 30 sn içinde
   yanıt vermiyor. Nadir; PORT env'inin Railway'ce otomatik verildiğini ve
   startCommand'ın `${PORT:-8000}` kullandığını doğrula (kullanıyor).
5. **Crash loop sonrası servis kapalı kalıyor** → restartPolicy ON_FAILURE
   maxRetries=5: beş başarısız denemeden sonra durur. Kökü çöz, sonra
   "Redeploy" ile yeniden başlat.

## C. Çökme yok ama "arada gidiyor" hissi

- Hobby plan uyku moduna geçmez ama tek instance'tır: deploy sırasında ~30-60 sn
  kesinti normaldir. Mobil istemci zaman aşımı + tekrar dene akışı bunu tolere eder.
- PostHog/Sentry'de 5xx oranına bak; `GeminiUnavailable` artışı Gemini kesintisidir,
  Railway değil (fallback devrede — log'da "fallback'e geçiliyor" ara).

## Kalıcı çözüm kontrol listesi (lansman öncesi, 8.7 ile birlikte)

- [ ] Cron servisi Config-as-code = `/railway.cron.toml` (A.1 — tek seferlik).
- [ ] Web + cron Variables eşit: Supabase üçlüsü + `ENV=prod` + `CRON_SECRET`.
- [ ] Sentry alarmı: "Deploy Crashed" yerine gerçek hata izi için SENTRY_DSN set.
- [ ] `GEMINI_MODEL=gemini-3.1-pro-preview` geçişi sonrası logda "fallback"
      taraması yap — sık görünüyorsa preview kota/erişim sorunu var demektir.
      **Paid tier açılmadan lansman yapılmaz** (~250 req/gün ücretsiz tavan).
      Fallback 2.5 flash/pro env'de kalır; silinmez.

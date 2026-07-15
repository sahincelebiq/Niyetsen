# Railway deployment

Niyetsen uses two Railway services from the same repository and backend root.

## API service

- Root directory: `/niyetsen-backend`
- Config path: `/railway.api.toml`
- Required variables: `ENV=prod`, `AUTH_DISABLED=false`,
  `USE_SUPABASE_DB=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
  `GEMINI_API_KEY`, `UNSPLASH_ACCESS_KEY`, `CRON_SECRET`,
  `CORS_ALLOWED_ORIGINS`
- `CORS_ALLOWED_ORIGINS` is a comma-separated exact-origin allowlist for web
  clients (for example `https://app.niyetsen.com,http://localhost:8082`).
  Native Expo clients do not need a CORS entry.
- Generate `CRON_SECRET` as a long random value. Never commit it.

## Cron service

- Create a second service from the same repository.
- Root directory: `/niyetsen-backend`
- Config path: `/railway.cron.toml`
- **Önerilen (direct mod):** API ile aynı Supabase env'leri + `CRON_EXECUTION_MODE=direct`
  - `ENV=prod`, `USE_SUPABASE_DB=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
  - `CRON_SECRET` (API ile aynı değer — doğrulama scriptleri için)
- **Yedek (http mod):** `API_BASE_URL` + `CRON_SECRET` (yavaş / timeout riski)
- Senkron: `python -m scripts.sync_cron_railway_env`
- Railway runs this service every five minutes in UTC. The API determines each
  user's local date/time and all jobs are idempotent.

The cron process must exit after each run. `scripts/cron_paused.py` geçici
duraklatma içindir (exit 0, mail yok). Normal iş için `run_scheduled_jobs.py`.

**Cron duraklatma:** `railway.cron.toml` → `startCommand = python scripts/cron_paused.py`
**Cron devam:** `startCommand = python scripts/run_scheduled_jobs.py` + redeploy

## Verification

1. Open the API `/health` endpoint and expect HTTP 200.
2. Cron servisinde **Config-as-code path** = `/railway.cron.toml` (uvicorn değil).
3. Trigger the cron service once from Railway.
4. **Direct mod logları** (doğru):
   - `cron modu: direct`
   - `close-day: {"processed_users":…,"failed_users":0,…}`
   - `cron tamamlandı (exit 0)`
5. **Yanlış mod** (düzelt): `POST /cron/close-day HTTP/1.1` → cron servisi
   `railway.toml` ile uvicorn çalıştırıyor; config path'i `/railway.cron.toml` yap.
6. Lokal kontrol: `python -m scripts.verify_railway_cron_runtime`

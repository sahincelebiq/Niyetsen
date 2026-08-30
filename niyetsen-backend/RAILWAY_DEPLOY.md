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
  - **`CRON_SKIP_PUSH=false` (prod cron):** `true` ise günlük görev push’u hiç gitmez.
    Lokal/örnek varsayılan `true` (spam yok). Expo Go uzak push taşımaz; lisans
    testi EAS/Play derlemesi + token (onboarding veya Profil) ister.
- **Yedek (http mod):** `API_BASE_URL` + `CRON_SECRET` (yavaş / timeout riski)
- Senkron: `python -m scripts.sync_cron_railway_env`
- Railway runs this service every five minutes in UTC. The API determines each
  user's local date/time and all jobs are idempotent.

The cron process must exit after each run. `scripts/cron_paused.py` geçici
duraklatma içindir (exit 0, mail yok). Normal iş için `run_scheduled_jobs.py`.

**Cron duraklatma (mail kes):**
```bash
cd niyetsen-backend
python -m scripts.pause_railway_cron   # toml → cron_paused + redeploy
git add railway.cron.toml && git commit -m "chore: cron duraklat" && git push
```
**Cron devam:**
```bash
python -m scripts.resume_railway_cron
git add railway.cron.toml && git commit -m "faz4: cron direct devam" && git push
```

## Cursor Railway MCP (kırmızı / Error)

**Sebep:** Cursor Railway eklentisi `railway mcp` çalıştırır. CLI yoksa veya Cursor'un PATH'i
`~/.npm-global/bin` içermiyorsa log: `spawn railway ENOENT`.

### Seçenek A — Remote MCP (CLI gerekmez, önerilen)

Proje `.cursor/mcp.json` içinde:
```json
"railway-remote": { "url": "https://mcp.railway.com" }
```
Cursor → Settings → Tools & MCP → **railway-remote** → Connect (OAuth).

### Seçenek B — Local MCP (CLI + tam yol)

```bash
npm install -g @railway/cli
railway login
```

`~/.cursor/mcp.json` (veya proje `.cursor/mcp.json`) — **sadece `railway` komutu yetmez**;
Cursor minimal PATH kullanır. Node ile tam yol kullan:

```json
"railway": {
  "command": "/usr/local/bin/node",
  "args": [
    "/Users/haze/.npm-global/lib/node_modules/@railway/cli/bin/railway.js",
    "mcp"
  ]
}
```

`railway mcp install --agent cursor` da ekler ama ENOENT devam ederse yukarıdaki tam yolu kullan.
**Reload Window** (`Cmd+Shift+P`). Eski kırmızı **Railway plugin** duplicate ise birini kapat.

### CLI yokken alternatif

Repo scriptleri (Project-Access-Token `.railway-project-token`):
- `python -m scripts.verify_cron_config`
- `python -m scripts.sync_cron_railway_env`
- `python -m scripts.railway_redeploy`
- `python -m scripts.pause_railway_cron`

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

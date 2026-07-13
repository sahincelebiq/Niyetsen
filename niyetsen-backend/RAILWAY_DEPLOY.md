# Railway deployment

Niyetsen uses two Railway services from the same repository and backend root.

## API service

- Root directory: `/niyetsen-backend`
- Config path: `/railway.api.toml`
- Required variables: `ENV=prod`, `AUTH_DISABLED=false`,
  `USE_SUPABASE_DB=true`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
  `GEMINI_API_KEY`, `UNSPLASH_ACCESS_KEY`, `CRON_SECRET`,
  `REVENUECAT_WEBHOOK_SECRET`, `CORS_ALLOWED_ORIGINS`
- `CORS_ALLOWED_ORIGINS` is a comma-separated exact-origin allowlist for web
  clients (for example `https://app.niyetsen.com,http://localhost:8082`).
  Native Expo clients do not need a CORS entry.
- Generate `CRON_SECRET` as a long random value. Never commit it.

## Cron service

- Create a second service from the same repository.
- Root directory: `/niyetsen-backend`
- Config path: `/railway.cron.toml`
- Required variables: `API_BASE_URL` (the API service HTTPS URL) and the same
  `CRON_SECRET`
- Railway runs this service every five minutes in UTC. The API determines each
  user's local date/time and all jobs are idempotent.

The cron process must exit after each run. `scripts/run_scheduled_jobs.py`
does so and returns a non-zero exit code if a job fails.

## Verification

1. Open the API `/health` endpoint and expect HTTP 200.
2. Trigger the cron service once from Railway.
3. Confirm `/cron/close-day` returns 200 in the cron logs.
4. Confirm only tasks whose local day has closed are changed and `point_log`
   contains the resulting penalty.
5. Response body may include `failed_users` and `user_errors` — ideal is `0`.
6. Run `RUN_IN_SUPABASE_SQL_EDITOR.sql` in Supabase SQL Editor after deploy
   (adds `subscription_expires_at`, repairs empty `categories`, backfills `streaks`).

## After git push

If Railway is GitHub-connected, API and cron redeploy automatically. Otherwise:

1. Railway → **api** service → Deploy → **Redeploy**
2. Railway → **cron** service → Deploy → **Redeploy**
3. Cron variables: `API_BASE_URL=https://api-production-86f1.up.railway.app`,
   `CRON_SECRET` must match the API service value.
4. Double-check health: `curl -sS https://api-production-86f1.up.railway.app/health`
5. Cron logs should show `close-day: 200` and `notifications: 200`.

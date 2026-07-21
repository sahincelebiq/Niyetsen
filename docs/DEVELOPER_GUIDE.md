# Niyetsen — Developer Guide

*Getting a new engineer from zero to a running app. Covers backend + mobile
local setup, environment variables, testing, and deployment. / Sıfırdan çalışan
uygulamaya. Backend + mobil kurulum, ortam değişkenleri, test, deploy.*

---

## 0. Prerequisites / Ön koşullar

- **Python** 3.11+
- **Node.js** 18+ and npm
- **Expo CLI** (via `npx expo`, no global install needed)
- Accounts / keys (ask the project owner): **Gemini API key**, **Supabase**
  project access, optionally **Unsplash**, **RevenueCat**, **Sentry**, **PostHog**.

> 🔑 **Secrets never go in code or in chat.** Put them only in the local `.env`
> files described below (they are gitignored). If you receive a key by an
> insecure channel, ask the owner to rotate it.

---

## 1. Clone

The parent repo and `mobile/` are **two separate git repositories**.

```bash
# parent repo (backend, docs, website)
git clone <parent-repo-url> Niyetsen
cd Niyetsen

# mobile is its own repo (nested; ignored by the parent)
cd mobile
git clone <mobile-repo-url> .   # if not already present
cd ..
```

---

## 2. Backend — local setup

```bash
cd niyetsen-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env — see §2.1
```

Run tests (no API key required — they use in-memory storage):
```bash
pytest -q                          # ~166 tests should pass
```

Run the API:
```bash
uvicorn app.main:app --reload
# Swagger UI: http://127.0.0.1:8000/docs
```

In dev, auth is disabled by default (`AUTH_DISABLED=true`): send an
`X-User-Id: sahin` header to identify a user. Without an Unsplash key, plan
images fall back to placeholders — the core loop still works.

### 2.1 Backend environment variables (`.env`)

| Variable | Required? | Notes |
|----------|-----------|-------|
| `GEMINI_API_KEY` | Yes (for AI) | Chat, plan, vision proof, embeddings. |
| `ENV` | — | `dev` (default) or `prod`. |
| `AUTH_DISABLED` | — | `true` in dev only; **forced false in prod**. |
| `USE_SUPABASE_DB` | prod: yes | `false` = in-memory (dev/tests); `true` = Postgres. |
| `SUPABASE_URL` | prod | Project URL. |
| `SUPABASE_SERVICE_KEY` | prod | `service_role` key — **backend only**, bypasses RLS. |
| `CRON_SECRET` | prod | Shared secret for cron endpoints (`X-Cron-Secret`). |
| `CORS_ALLOWED_ORIGINS` | prod | Comma-separated web-origin allow-list. |
| `UNSPLASH_ACCESS_KEY` | optional | Plan images; falls back to placeholder. |
| `REVENUECAT_WEBHOOK_SECRET` / `REVENUECAT_API_KEY` | prod | Subscription webhook verify + sync. |
| `SENTRY_DSN` | optional | Error tracking. |
| `RAG_ENABLED` / `RAG_EMBEDDINGS_ENABLED` | — | Default on; embeddings off → keyword fallback. |
| `DEV_ACCOUNT_EMAILS` | — | Comma-separated full-access dev accounts. |

Full list with defaults: `app/config.py`. Game constants (points, penalties,
rank ladder, fortune rights) are also there — **locked; do not change without
Master Plan §1**.

---

## 3. Mobile — local setup

```bash
cd mobile
npm install
cp .env.example .env               # then edit — see §3.1
node scripts/verify-env.mjs        # optional sanity check
npx expo start
```

Open on:
- **iOS simulator** / **Android emulator** — press `i` / `a` in the Expo CLI.
- **Physical device (Expo Go)** — scan the QR; device and Mac must share Wi-Fi,
  and `EXPO_PUBLIC_API_URL` must point to your Mac's LAN IP
  (`ipconfig getifaddr en0`), not `localhost`.

> ⚠️ **RevenueCat purchases do NOT work in Expo Go.** You need an EAS/dev build
> to test IAP.

### 3.1 Mobile environment variables (`.env`)

All client env vars are prefixed `EXPO_PUBLIC_` (they ship in the app bundle, so
**never** put a service-role or private key here — publishable/anon keys only).

| Variable | Notes |
|----------|-------|
| `EXPO_PUBLIC_API_URL` | Backend base URL. Simulator: `http://localhost:8000`; Android emulator: `http://10.0.2.2:8000`; device: `http://<Mac-LAN-IP>:8000`; prod: Railway HTTPS URL. |
| `EXPO_PUBLIC_SUPABASE_URL` | Supabase project URL. |
| `EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Anon/publishable key (safe for client). |
| `EXPO_PUBLIC_POSTHOG_KEY` / `_HOST` | Analytics (optional; silent if empty). |
| `EXPO_PUBLIC_REVENUECAT_API_KEY` (or per-platform `_IOS_`/`_ANDROID_`) | RevenueCat public key. |
| `EXPO_PUBLIC_RC_ENTITLEMENT_ID` | Must match RevenueCat dashboard (`premium`). |
| `EXPO_PUBLIC_SENTRY_DSN` | Optional; enable in production builds. |

Ship-time secrets go in **EAS Secrets**, not the repo:
```bash
eas secret:create --scope project --name EXPO_PUBLIC_API_URL --value https://<railway-url>
```

---

## 4. Database (Supabase)

Migrations live in `niyetsen-backend/supabase/migrations/` (17 timestamped SQL
files). Apply them in order to a fresh Supabase project, or use the consolidated
`RUN_IN_SUPABASE_SQL_EDITOR.sql` in the Supabase SQL editor. Verify connectivity:

```bash
cd niyetsen-backend
python -m scripts.smoke_test_supabase
```

---

## 5. Deployment (Railway)

Two services from the same repo, both rooted at `/niyetsen-backend`:
- **API service** — config `railway.api.toml`.
- **Cron service** — config `railway.cron.toml`; runs every 5 min (UTC). Jobs
  are idempotent and compute each user's local time.

Full instructions, required prod variables, and cron pause/resume:
`niyetsen-backend/RAILWAY_DEPLOY.md`.

Mobile is built & submitted via **EAS** (`mobile/eas.json`).

---

## 6. Working conventions (from `CLAUDE.md`)

- **Build order = Master Plan phases.** Do not skip a phase or pass a "KAPI"
  (gate) without meeting its criteria.
- **Small commits**, prefixed e.g. `faz3: proof upload + vision score`.
- **Test every endpoint by hand; test every screen on a real device (Expo Go).**
- **Don't invent the DB schema** — it is Master Plan §2.
- When unsure: Master Plan §1 → else ask the owner. Don't fabricate.

---

## 7. Common gotchas / Sık karşılaşılan sorunlar

| Symptom | Fix |
|---------|-----|
| Device can't reach backend | Use Mac LAN IP in `EXPO_PUBLIC_API_URL`, not `localhost`; same Wi-Fi. |
| IAP not working in Expo Go | Expected — build with EAS/dev build. |
| Backend won't boot in prod | A safety-lock failed (auth/db/cron/webhook secret) — read the error; it names the fix. `app/main.py`. |
| AI calls fail locally | `GEMINI_API_KEY` missing/invalid in `.env` (not in code). |
| Plan images are placeholders | `UNSPLASH_ACCESS_KEY` not set — harmless in dev. |

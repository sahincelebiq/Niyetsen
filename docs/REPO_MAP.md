# Niyetsen — Repository Map / Depo Haritası

*"What is where" — a directory-by-directory guide. / "Neyin nerede olduğu" —
dizin dizin rehber.*

> ⚠️ `mobile/` is its **own git repository** (nested, gitignored by the parent).
> Clone/commit it separately. / `mobile/` **ayrı bir git deposudur** (üst depo
> onu ignore eder). Ayrı klonlanır/commit'lenir.

---

## Top level / Kök dizin

| Path | Purpose / Açıklama |
|------|--------------------|
| `README.md` | Entry point / giriş noktası. |
| `NIYETSEN_MASTER_PLAN.md` | **Single source of truth** — phases, locked decisions (§1), data model (§2). / **Tek gerçek kaynak.** |
| `CLAUDE.md`, `AGENTS.md` | AI agent working rules (Cursor + Claude Code). / AI ajan çalışma kuralları. |
| `README_BACKEND.md` | Backend deep-dive & extension slots. / Backend derinlemesine anlatım. |
| `STORE_READINESS.md` | App Store / Play submission checklist. / Mağaza yayın listesi. |
| `.gitignore`, `.mcp.json` | Repo + MCP config. |
| `niyetsen-backend/` | Python/FastAPI backend. |
| `mobile/` | Expo app (separate git repo). |
| `website/` | Marketing site + blog (static HTML/CSS). / Tanıtım sitesi + blog. |
| `docs/` | All documentation. / Tüm dokümanlar. |
| `logo/`, `_design_ref/` | Brand assets & design references. / Marka ve tasarım varlıkları. |
| `_tmp_assets/` | **Gitignored** — local-only temp files (e.g. Expo Go QR PNG). / Yerel geçici dosyalar. |
| `_arsiv/` | Old zip backups (gitignored). / Eski zip yedekleri. |

---

## `docs/` — Documentation / Dokümanlar

| Path | Purpose |
|------|---------|
| `README.md` | Docs index / doküman dizini. |
| `ARCHITECTURE.md` | System & backend/mobile architecture. |
| `SECURITY.md` | Security overview + audit. |
| `REPO_MAP.md` | This file. |
| `DEVELOPER_GUIDE.md` | Local setup, env vars, running & testing. |
| `AGENT_HANDOFF.md`, `MANUS_CURSOR_SYNC.md` | Agent-to-agent handoff notes. |
| `FAZ5_AKTIF.md`, `FAZ7_V2_FAL_RAG.md` | Phase working docs (history/context). |
| `KAPI5_REVENUECAT_SETUP.md`, `ODEME_ANAHTARLARI.md` | Payment / RevenueCat setup notes. |
| `arsiv-planlama/` | **Archived** original planning docs (`.docx`/`.xlsx`, June 2026). Superseded by `NIYETSEN_MASTER_PLAN.md` — kept for history, not authoritative. / Arşivlenmiş eski planlama belgeleri; artık MASTER_PLAN geçerli. |

---

## `niyetsen-backend/` — Backend

| Path | Purpose |
|------|---------|
| `app/main.py` | Entry point; prod safety-locks; security middleware. |
| `app/config.py` | All settings from env + **locked game constants**. |
| `app/api/routes.py` | 38 HTTP endpoints; JWT auth; rate limits. |
| `app/core/` | Prompts, prompt builder, Gemini client, tools allow-list, philosophy, rate limit, dev accounts, observability. |
| `app/services/` | Business logic — one file per concern (intent, plan, proof, scoring, project, fortune, rag, subscription, consent, notification, push…). |
| `app/models/schemas.py` | Pydantic API contracts. |
| `app/storage/` | Repository interface + InMemory + Supabase implementations. |
| `knowledge/` | RAG knowledge base (`.md`): atomik_aliskanliklar, burclar, felsefe, idoller, motivasyon, senaryolar, tarot. **Lives here so it deploys to Railway.** |
| `tests/` | 175 test functions (pytest). `test_scoring`-style files encode the game-rule contract. |
| `scripts/` | Ops scripts: Railway cron pause/resume/redeploy, env sync, RevenueCat/KAPI setup & verification, Supabase smoke test. |
| `supabase/migrations/` | 17 timestamped SQL migrations + `RUN_IN_SUPABASE_SQL_EDITOR.sql`. |
| `Dockerfile`, `railway*.toml` | Deploy config (API + cron services). |
| `RAILWAY_DEPLOY.md` | Railway two-service deployment guide. |
| `.env`, `.env.example`, `.env.stripe.local` | Secrets (**`.env` gitignored**) + placeholder template. |

### Endpoint groups (`app/api/routes.py`)
- **Health:** `GET /health`
- **Chat:** `/chat`, `/chat/history`, `/chat/reset`, `/chat/threads*`,
  `/chat/greeting`, `/chat/session`, `/chat/attachment`
- **Projects/Plans:** `/projects*`, `/plan`, `/plan/generate`, `/plan/next`,
  `/tasks/daily`
- **Tasks:** `/task/{id}/proof`, `/task/{id}/excuse`
- **Cron:** `/cron/close-day`, `/cron/notifications`
- **Bonus:** `/bonus/offer`, `/bonus/active`, `/bonus/{id}/complete`
- **User/Me:** `/me/state`, `/me/profile`, `/me/push-token`, `/me/consent`,
  `DELETE /me`
- **Subscription:** `/me/subscription`, `/me/subscription/sync`,
  `/webhooks/revenuecat`
- **Fortune (fal):** `/paths`, `/fortune/rights`, `/fortune/tarot`,
  `/fortune/photo/{kind}`, `/fortune/history`, `/fortune/horoscope`

---

## `mobile/` — Expo app (separate git repo)

| Path | Purpose |
|------|---------|
| `src/app/` | Screens (expo-router file routes) + `legal/`. |
| `src/components/` | Reusable UI (+ `.web.tsx` web variants). |
| `src/lib/` | API client, Supabase client, storage, purchases. |
| `src/providers/`, `src/hooks/`, `src/constants/` | Context, hooks, theme/copy/legal. |
| `app.json`, `eas.json` | Expo + EAS build config. Bundle `com.niyetsen.app`. |
| `.env`, `.env.example` | `EXPO_PUBLIC_*` client config (**`.env` gitignored**). |
| `dist/` | Built web export (generated). |
| `scripts/verify-env.mjs` | Env sanity check. |

---

## `website/` — Marketing site

Static HTML/CSS/JS: landing (`index.html`), legal pages (`gizlilik.html`,
`kullanim-kosullari.html`), a dev-log (`gelistirme.html`), a `blog/` with SEO
articles, `css/`, and `sitemap.xml`.

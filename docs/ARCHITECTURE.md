# Niyetsen — Architecture

*Technical overview for engineers joining the project. For the roadmap and
locked product decisions, `NIYETSEN_MASTER_PLAN.md` is the single source of
truth; where it conflicts with anything here, the Master Plan wins.*

---

## 1. System context

Niyetsen is a two-tier system plus managed third-party services:

| Tier | Tech | Role |
|------|------|------|
| **Mobile client** | Expo (React Native + TypeScript, expo-router) | UI, camera capture, auth, IAP. Lives in `mobile/` as its **own git repository**. |
| **Backend API** | Python 3.11+, FastAPI | The "core brain": chat, plan generation, scoring engine, proof verification, prompt assembly. Lives in `niyetsen-backend/`. |
| Database / Auth / Storage | Supabase (Postgres + Auth + Storage) | Persistence, JWT issuance, proof-photo buckets. |
| AI | Google Gemini — **4 models, each with a distinct role** (see below) | Chat, plan generation, **photo-proof vision verification**, image generation, RAG embeddings. |
| Images | Unsplash + Gemini image model (hybrid) | Illustrated plan tiles. |
| Subscriptions | RevenueCat (IAP only) | Monthly / yearly premium entitlement. |
| Observability | Sentry (errors), PostHog (analytics) | Optional; silent if unconfigured. |
| Scheduling | Railway cron (every 5 min, UTC) | Day-close penalties, streak logic, notifications. |

The mobile app talks to the backend over HTTPS with a Supabase-issued JWT on
every request. The backend holds all secrets and business logic; the client is
deliberately "thin" on rules.

### Gemini models — one gateway, four roles

All calls go through the single gateway `core/gemini_client.py` (retry/backoff/
JSON-parse), but each use case is pinned to a different model (`app/config.py`):

| Model | Config var | Used for |
|---|---|---|
| `gemini-2.5-flash` | `GEMINI_MODEL` | Chat (`intent_service`), fortune module, photo-proof vision verification, image-search-term enrichment. |
| `gemini-2.5-pro` | `GEMINI_MODEL_PLAN` | **Plan generation** (`plan_service.py`) — needs stronger reasoning for the batched daily-task JSON. |
| `gemini-2.5-flash-image` ("**Nano Banana**") | `GEMINI_MODEL_IMAGE` | **Image generation** (`gemini_client.generate_image_bytes`) — hybrid with Unsplash for plan tile illustrations. |
| `gemini-embedding-001` | `GEMINI_EMBED_MODEL` | RAG chunk embeddings (`rag_service.py`). |

---

## 2. Backend architecture (`niyetsen-backend/`)

Layered, with a strict rule: **`api/` has no business logic, `services/` has no
HTTP.** The scoring engine is pure (no DB/HTTP/AI) so it can be 100% unit-tested.

```
app/
├── main.py                 App entry. Prod safety-locks, CORS, security
│                           middleware (body cap + headers), global error handler.
├── config.py               ALL settings from env. Locked game constants live here
│                           (points, penalties, rank ladder, fortune rights).
├── api/
│   └── routes.py           HTTP gateway (~42 endpoints): auth (JWKS JWT), rate
│                           limiting, request/response schemas, error translation.
├── core/
│   ├── prompts.py          All prompt text (tone change = only here).
│   ├── prompt_builder.py   Immutable order: SYSTEM → CONTEXT(RAG+memory) → USER.
│   ├── gemini_client.py    Single gateway to Gemini: retry/backoff/JSON-parse.
│   ├── tools.py            Function-calling ALLOW-LIST (closed set).
│   ├── philosophy.py       The product "constitution" (read first).
│   ├── rate_limit.py       slowapi limiter (per-user).
│   ├── dev_accounts.py     Dev-only full-access accounts (no store purchase).
│   └── observability.py    Sentry init.
├── services/               Business logic (one concern per file):
│   ├── intent_service      Intent gathering + crisis safety-net + readiness lock
│   ├── plan_service        Batched plan generation (never 365 days in one call)
│   ├── image_service       Unsplash/Gemini hybrid → image URLs
│   ├── proof_service       Vision confidence score + 3-attempt compassion rule
│   ├── scoring_service     PURE game engine — no DB/HTTP/AI, fully tested
│   ├── project_service     Multi-plan "project" slots
│   ├── fortune_service     Tarot / coffee / palm / horoscope (fal module)
│   ├── rag_service         Gemini embedding + in-memory cosine retrieval
│   ├── subscription_service / revenuecat_client   RevenueCat entitlements
│   ├── consent_service     KVKK/GDPR consent versions
│   ├── notification_service / push_service         Push + scheduled notifications
│   └── (bonus, greeting, path, profile, task_lifecycle, tool, attachment)
├── models/
│   └── schemas.py          Pydantic API contracts (mobile derives types from these).
└── storage/
    ├── repository.py       Repository interface + InMemory impl (tests/MVP default)
    └── supabase_repository.py   Real Postgres persistence (prod)
```

### Storage strategy
A `Repository` interface has two implementations selected at runtime by
`USE_SUPABASE_DB`:
- **InMemoryRepository** — default in dev and tests (no DB needed).
- **SupabaseRepository** — Postgres persistence in prod. Uses the Supabase
  `service_role` key, which **bypasses RLS and never leaves the backend**.

`main.py` refuses to boot in prod unless `USE_SUPABASE_DB=true` (see §5).

### AI request assembly (locked order)
Every `/chat` call is assembled in exactly one place (`core/prompt_builder.py`):
1. **SYSTEM** — fixed system prompt (in `core/prompts.py`).
2. **CONTEXT** — RAG chunks (labelled) + dynamic user-memory block.
3. **USER** — the user message.

User input **never** enters the SYSTEM role. RAG content is always fenced inside
a labelled CONTEXT block — this is a prompt-injection guardrail, not a
convenience.

### Function calling (closed allow-list)
The model may only invoke a fixed set of tools (`core/tools.py`): `alarm_kur`,
`takvime_ekle`, `gorev_olustur`, `kanit_dogrula`, `puan_guncelle`,
`gorev_ertele_mazeretli`, plus `harita_yer_getir` / `pinterest_gorsel_getir`
(v2). Anything else (payments, ticketing, file ops) is rejected by
`is_allowed`.

### The scoring engine (the heart)
`services/scoring_service.py` is a **pure function** module encoding the locked
game rules from `config.py` / Master Plan §1:
- Task completion: **+50** per tagged category.
- Silent miss penalty: **−25 × 2ⁿ**, capped at **200**; any completion resets n.
- Excuse path: flat **−25** (no doubling); **10 excuses → all points × 0.5**.
- Points floor **0** (never negative).
- Streak: ≥1 task/day continues; day boundary at user-timezone 23:59; one
  Chain-Protection token auto-granted per month.

`tests/` encodes these as a contract — a red test means a rule was broken.

---

## 3. Mobile architecture (`mobile/`)

Expo app, file-based routing (`expo-router`). **Separate git repository.**

```
mobile/src/
├── app/            Screens (routes): index, daily, explore, rank, bonus, paywall,
│                   settings, fal, fal-gecmisi, tarot, astroloji, mystic, yollar,
│                   and legal/ (consent, privacy, terms, kvkk).
├── components/     Reusable UI (chat composer, consent gate, subscription gate,
│                   onboarding, streak pill, project sheets, themed primitives…).
│                   Note `.web.tsx` variants for web-specific rendering.
├── lib/            API client, Supabase client, storage, purchases (RevenueCat).
├── providers/      React context providers (auth, subscription, etc.).
├── hooks/          Custom hooks.
├── constants/      theme, copy, legal text.
└── global.css      NativeWind / Tailwind styles.
```

- **Auth** — Supabase (`@supabase/supabase-js`) + Apple/Google auth session.
  Tokens stored in `expo-secure-store` (never `localStorage`).
- **Purchases** — `react-native-purchases` (RevenueCat). Purchases require an
  EAS/dev build — they do **not** work in Expo Go.
- **Config** — `EXPO_PUBLIC_*` env vars only (client-safe). The service-role key
  is **never** shipped to the client — only the Supabase publishable/anon key.
- Builds & submission via EAS (`eas.json`). Bundle id `com.niyetsen.app`.

---

## 4. Request lifecycle (example: photo proof)

```
1. User completes a task, takes an in-app photo.
2. Mobile → POST /task/{id}/proof   (multipart, ≤5MB, JWT header)
3. routes.py       : validate JWT (JWKS), rate-limit, size/type check
4. proof_service   : send image to Gemini Vision → confidence score
5. scoring_service : if score ≥ 60 → approve, +points; else gentle retry
                     (max 3 attempts; 3rd attempt accepted on user's word)
6. storage         : persist proof + updated state (Supabase in prod)
7. Mobile ← updated points / streak
```

The **Railway cron** service runs every 5 minutes (UTC), calls the day-close and
notification jobs; the API computes each user's local date so jobs are
timezone-correct and idempotent.

---

## 5. Production safety-locks (`app/main.py`)

The backend **refuses to start** in `ENV=prod` if any of these hold — this makes
insecure production deploys structurally impossible:

| Condition | Why it's fatal |
|---|---|
| `AUTH_DISABLED=true` | Would expose every endpoint without a JWT. |
| `USE_SUPABASE_DB=false` | Would run on in-memory storage → silent data loss. |
| `CRON_SECRET` empty | Cron endpoints would be unauthenticated. |
| `REVENUECAT_WEBHOOK_SECRET` empty | Subscription webhooks would be forgeable. |

See [`SECURITY.md`](SECURITY.md) for the full security posture.

---

## 6. Key third-party accounts (identifiers, not secrets)

- **Supabase** project: `ktweahgrrppmxpdhohdh`
- **Mobile bundle id**: `com.niyetsen.app` (iOS + Android), Expo owner `sahincelebiq`
- **Backend hosting**: Railway (two services — API + cron, same repo/root)

All corresponding **secret keys** live only in `.env` / Railway variables / EAS
secrets — never in the repository.

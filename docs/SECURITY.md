# Niyetsen — Security Overview & Audit

*Prepared for external technical review (investor due diligence). Summarises the
security posture of the backend and mobile client, plus a point-in-time audit of
the repository. Reviewed: 2026-07-21.*

---

## 1. Executive summary

Niyetsen's security posture is **solid for its stage**. The backend is built so
that an insecure production deploy is *structurally impossible* (boot-time
safety-locks), secrets are correctly kept out of version control, authentication
is standards-based (Supabase JWT via JWKS), and there is a defence-in-depth
middleware layer. No secrets, `.env` files, or credentials are committed to the
repository.

The findings below are **hardening opportunities**, not active vulnerabilities.

---

## 2. Secret management ✅

- **All secrets live only in `.env`** (backend) / EAS Secrets & `EXPO_PUBLIC_*`
  (mobile) / Railway variables. Code reads them via `os.environ` in one place
  (`app/config.py`).
- **`.env` and all secret files are gitignored and verified untracked.** Audited
  files: `niyetsen-backend/.env`, `.env.stripe.local`, `.railway-project-token`,
  `.railway-revenuecat-secret`, `mobile/.env` — all return `git check-ignore`
  positive (ignored).
- **No tracked secrets.** `git ls-files` shows no `.env`, `.pem`, `.key`,
  service-account, or credential files. The only tracked env file is
  `.env.example` — a placeholder-only template (verified: no real values).
- **No tracked `.DS_Store`** files.
- The Supabase **`service_role`** key (bypasses RLS) is used **only in the
  backend** and never shipped to the client. The mobile app uses only the
  publishable/anon key.

> ⚠️ **Operational note:** Because Şahin has, in the past, pasted real
> credentials into chat/tools, treat any key that has ever appeared outside
> `.env` as compromised and **rotate it**. Rotating is cheap; assuming safety is
> not. This is a process reminder, not a repo finding.

---

## 3. Authentication & authorization ✅

- **Supabase JWT on every request** except `/health`, verified in
  `api/routes.py > get_current_user`.
- Uses **JWKS (RS256/ES256)** via `PyJWKClient` against
  `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` — the modern asymmetric scheme,
  not the deprecated shared HS256 legacy secret. No shared signing secret to leak.
- **Dev bypass is impossible in prod:** `AUTH_DISABLED=true` is only honoured in
  `ENV=dev`; `main.py` raises at boot if prod + auth disabled.

---

## 4. Production boot-time safety-locks ✅ (notable strength)

`app/main.py` refuses to start in `ENV=prod` when any hold:

| Lock | Prevents |
|---|---|
| `AUTH_DISABLED` must be false | Unauthenticated endpoints |
| `USE_SUPABASE_DB` must be true | Silent data loss on in-memory storage |
| `CRON_SECRET` must be set | Unauthenticated cron endpoints |
| `REVENUECAT_WEBHOOK_SECRET` must be set | Forgeable subscription webhooks |

This "fail-closed at boot" pattern is a strong control — misconfiguration
crashes the deploy instead of silently shipping an insecure service.

---

## 5. Transport & HTTP hardening ✅

Implemented in the `security_layer` middleware (`app/main.py`):
- **Request-body cap:** hard 10MB ceiling on all endpoints (second line of
  defence against memory-DoS; multipart proof endpoints add their own 5MB limit).
- **Security headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options:
  DENY`, `Referrer-Policy: no-referrer`; `Cache-Control: no-store` on
  personal-data responses; `Strict-Transport-Security` (HSTS) in prod.
- **CORS:** wildcard only in dev; prod uses an explicit comma-separated origin
  allow-list (`CORS_ALLOWED_ORIGINS`). Native Expo clients are not subject to CORS.
- **Safe error responses:** the global exception handler returns a generic
  message to the client and logs full detail server-side (→ Sentry). No internal
  detail / stack leakage.

---

## 6. Abuse & AI-safety controls ✅

- **Per-user rate limits** (`slowapi`): chat 10/min, proof 12/min, plan 3/min,
  fortune 6/min — all env-tunable.
- **Prompt-injection guardrail:** user input never enters the SYSTEM role; RAG
  content is fenced in a labelled CONTEXT block; prompt assembly happens in one
  place (`core/prompt_builder.py`) in an immutable order.
- **Closed function-calling allow-list** (`core/tools.py`): the model cannot
  invoke anything outside a fixed set — no payment, file, or ticketing tools.
- **Photo proof validation:** server-side type/size checks (jpeg/png, ≤5MB),
  in-app camera only.
- **Content-safety net:** crisis-signal detection halts motivation/fortune flows
  and switches to a compassionate response; fortune responses carry an
  "entertainment only" disclaimer (store compliance).

---

## 7. Privacy & compliance ✅

- Versioned consent tracking (KVKK / GDPR): privacy policy, KVKK, AI-chat,
  proof-photo, and marketing consents each carry a version (`config.py`).
- **Account deletion** endpoint (`DELETE /me`) — user can erase their data;
  proof photos live in per-user Supabase Storage buckets.
- Data controller declared: Şahin Çelebi · ai@niyetsen.com.

---

## 8. Hardening opportunities (recommendations, not blockers)

Ranked by value. None is an active vulnerability.

1. **Rotate any credential ever exposed outside `.env`** (see §2 note). Highest
   priority because it's operational, not code.
2. **Dependency scanning in CI.** Add `pip-audit` (backend) and `npm audit` /
   Expo's vulnerability check (mobile) to a CI pipeline so new CVEs surface
   automatically. `requirements.txt` uses floors (`>=`) — consider pinning exact
   versions + a lockfile for reproducible, auditable builds.
3. **Secret-scanning pre-commit hook** (e.g. `gitleaks`) — a mechanical backstop
   for the "pasted secret" risk, given the history.
4. **RLS review.** Since the backend uses the `service_role` key (RLS-bypassing),
   confirm Postgres Row-Level Security is still enabled and correct as a
   defence-in-depth layer for any path that might use the anon key.
5. **Rate-limit backing store.** Confirm `slowapi` limits are backed by a shared
   store (e.g. Redis) rather than per-process memory once the API runs on more
   than one instance — otherwise limits are per-instance.
6. **`RUN_IN_SUPABASE_SQL_EDITOR.sql`** — ensure this convenience migration file
   never contains inline credentials before sharing the repo widely.

---

## 9. Audit method (reproducible)

```bash
# 1. Secret files are actually ignored
git check-ignore niyetsen-backend/.env niyetsen-backend/.env.stripe.local \
                  niyetsen-backend/.railway-project-token mobile/.env

# 2. No secrets tracked in git
git ls-files | grep -iE '\.env$|\.env\.|secret|credential|\.pem$|\.key$'
#   → expect only: .env.example  (placeholder template)

# 3. No tracked .DS_Store
git ls-files | grep -c .DS_Store            # → 0

# 4. .env.example carries no real values
git show HEAD:niyetsen-backend/.env.example
```

*This audit is point-in-time. Re-run before any external repository share and
after any dependency bump.*

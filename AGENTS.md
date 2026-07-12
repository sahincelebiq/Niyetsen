# AGENTS.md

## Cursor Cloud specific instructions

This repository's runnable code is the Python/FastAPI backend in `niyetsen-backend/`
(the top-level `*.docx`/`*.xlsx` files are product docs). Roadmap/rules live in
`NIYETSEN_MASTER_PLAN.md` and `CLAUDE.md`.

### Environment
- Python 3.12 with a virtualenv at `niyetsen-backend/.venv` (created by the startup
  update script). System package `python3.12-venv` is required to create the venv and
  is already provisioned in the VM snapshot.
- Activate with `source niyetsen-backend/.venv/bin/activate` (or call binaries via
  `niyetsen-backend/.venv/bin/...`). Run all commands below from `niyetsen-backend/`.

### Test / run
- Tests: `pytest -q` — 29 tests, no API key needed. `tests/conftest.py` forces
  `USE_SUPABASE_DB=false` so tests always use the in-memory repo.
- Dev server: `uvicorn app.main:app --reload` → Swagger at http://127.0.0.1:8000/docs.
- Lint: no linter is configured (no ruff/flake8/black config in the repo); `pytest`
  is the only automated check.

### Non-obvious gotchas
- Dev auth: send header `X-User-Id: <id>` on requests (`AUTH_DISABLED=true` by default).
- `app/config.py` has defaults for every setting, so the server boots with NO `.env`.
  Copy `.env.example` to `.env` only to add keys (`GEMINI_API_KEY`, `UNSPLASH_ACCESS_KEY`,
  Supabase). `.env` is gitignored.
- The AI-powered "rings" (`POST /chat`, `POST /plan/generate`, `POST /plan/next`,
  `POST /task/{id}/proof`) require `GEMINI_API_KEY`; without it `gemini_client.get_client`
  raises a deliberate `RuntimeError` surfaced as HTTP 500. This is expected, not a bug.
- The non-AI core game engine works fully WITHOUT any key: `GET /me/state`,
  `POST /cron/close-day`, `POST /task/{id}/excuse` (pure scoring/streak logic in
  `services/scoring_service.py`). Use these to smoke-test without credentials.
- `ENV=prod` hard-fails at import if `AUTH_DISABLED=true` or `USE_SUPABASE_DB=false`
  (`app/main.py` locks). Keep `ENV=dev` for local work.

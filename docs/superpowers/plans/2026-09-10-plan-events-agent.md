# Plan-içi ajan + etkinlik Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kök plana fotosuz etkinlik (tekrar kuralı + Bugün occurrence + Yaptım) ve Planım’a kilitli ajan sohbeti ekle; 365 üretim ve global sohbet kirlenmesin.

**Architecture:** `plan_events` / `plan_event_occurrences` ayrı tablolar. Materialize `GET /tasks/daily` içinde. Skor `scoring_service.complete_task`. Plan ajanı ayrı `kind=plan_agent` thread + `etkinlik_olustur`. In-memory + Supabase aynı `Repository` sözleşmesi.

**Tech Stack:** FastAPI, pytest in-memory repo, Supabase Postgres (RLS, text plan_id FK), Gemini tools kapalı liste.

## Global Constraints

- `plans.id` TEXT, uuid değil
- Migration Şahin SQL Editor’da; VERIFY `RUN_IN_SUPABASE_SQL_EDITOR.sql`
- `Easing`/`Animated` RN’den yok (bu dilim backend)
- Commit yalnız Şahin isteyince
- pytest yeşil kalır; model adı uydurulmaz
- Thread degrade: plan-içi sohbet hatası planı düşürmez

## File map

- `app/models/schemas.py` — event DTO + DailyTasksResponse.events
- `app/services/event_service.py` — kural, materialize, complete, kategori çıkarımı
- `app/services/plan_agent_service.py` — scoped chat
- `app/services/tool_service.py` — `etkinlik_olustur`
- `app/core/tools.py` — PLAN_AGENT declarations
- `app/core/prompts.py` — PLAN_AGENT_ADDENDUM
- `app/storage/base.py` + `repository.py` + `supabase_repository.py`
- `app/services/task_lifecycle_service.py` — close_day
- `app/services/recap_service.py` + `project_service.py` + `api/routes.py`
- `supabase/migrations/20260910120000_plan_events_agent.sql`
- `tests/test_plan_events.py`

---

### Task 1: Kırmızı testler

- [ ] `tests/test_plan_events.py` yaz (oluştur, Bugün, Yaptım, ceza yok, zincir kurtarma, thread gizleme, araç)
- [ ] `pytest tests/test_plan_events.py -q` kırmızı

### Task 2: Şema + servis + repo

- [ ] Migration + VERIFY satırları
- [ ] schemas, event_service, InMemory + ABC + Supabase
- [ ] Testler yeşil (HTTP + close_day)

### Task 3: Ajan + daily + recap

- [ ] tools, dispatch, plan_agent_service, routes, recap point_log
- [ ] `pytest -q` tam süit yeşil

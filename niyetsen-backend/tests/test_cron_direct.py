"""Tests for crash-safe Railway cron direct execution."""
from __future__ import annotations

from datetime import datetime, timezone

import scripts.run_scheduled_jobs as cron_jobs
from app.models.schemas import GameState, Plan, PlanDay, Task, UserProfile
from app.services.task_lifecycle_service import latest_closed_day
from app.storage.repository import InMemoryRepository


def test_run_jobs_completes_with_in_memory_repo(monkeypatch, capsys):
    repository = InMemoryRepository()
    user_id = "cron-direct"
    tz = "Europe/Istanbul"
    now_utc = datetime.now(timezone.utc)
    closed_day = latest_closed_day(now_utc, tz)
    repository.save_profile(user_id, UserProfile(timezone=tz))
    repository.save_plan(user_id, Plan(
        id="plan-cron",
        duration_days=1,
        batch_generated_until=1,
        start_date=closed_day,
        days=[PlanDay(day=1, tasks=[Task(
            id="task-due",
            day=1,
            title="Kapanacak gün",
            categories=["İrade"],
            date=closed_day,
        )])],
    ))
    repository.save_state(GameState(user_id=user_id))
    monkeypatch.setattr("app.storage.repository.repo", repository)

    warnings = cron_jobs.run_jobs()
    captured = capsys.readouterr()

    assert "close-day" in captured.out
    assert repository.get_task(user_id, "task-due").status == "missed_silent"


def test_main_always_exits_zero_even_on_job_error(monkeypatch):
    monkeypatch.setenv("USE_SUPABASE_DB", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")

    def boom():
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(cron_jobs, "run_jobs", boom)

    try:
        cron_jobs.main()
        exit_code = 0
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 0


def test_main_exits_zero_when_env_missing(monkeypatch, capsys):
    monkeypatch.delenv("USE_SUPABASE_DB", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    try:
        cron_jobs.main()
        exit_code = 0
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 0
    assert "env eksik" in capsys.readouterr().err.lower()


def test_secret_key_alias(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    cron_jobs._service_key_set()
    assert cron_jobs._service_key_set() is True

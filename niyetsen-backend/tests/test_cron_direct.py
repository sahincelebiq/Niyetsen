"""Tests for Railway cron direct execution."""
from __future__ import annotations

import scripts.run_scheduled_jobs as cron_jobs
from app.models.schemas import GameState, Plan, PlanDay, Task, UserProfile
from app.storage.repository import InMemoryRepository
from datetime import date


def test_run_jobs_completes_with_in_memory_repo(monkeypatch, capsys):
    repository = InMemoryRepository()
    user_id = "cron-direct"
    repository.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    repository.save_plan(user_id, Plan(
        id="plan-cron",
        duration_days=1,
        batch_generated_until=1,
        start_date=date(2026, 7, 14),
        days=[PlanDay(day=1, tasks=[Task(
            id="task-14",
            day=1,
            title="Dün",
            categories=["İrade"],
            date=date(2026, 7, 14),
        )])],
    ))
    repository.save_state(GameState(user_id=user_id))

    monkeypatch.setattr("app.storage.repository.repo", repository)

    hard, soft = cron_jobs.run_jobs()
    captured = capsys.readouterr()

    assert hard == []
    assert "close-day" in captured.out
    assert repository.get_task(user_id, "task-14").status == "missed_silent"


def test_main_exits_zero_on_soft_notification_failure(monkeypatch):
    monkeypatch.setenv("USE_SUPABASE_DB", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")

    def fake_jobs():
        return [], ["notifications: expo down"]

    monkeypatch.setattr(cron_jobs, "run_jobs", fake_jobs)

    try:
        cron_jobs.main()
        exit_code = 0
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code == 0


def test_require_direct_env_lists_missing(monkeypatch):
    monkeypatch.delenv("USE_SUPABASE_DB", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    import pytest
    with pytest.raises(RuntimeError, match="USE_SUPABASE_DB"):
        cron_jobs._require_direct_env()

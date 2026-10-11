"""Tests for crash-safe Railway cron direct execution."""
from __future__ import annotations

from datetime import date, datetime, timezone

import scripts.run_scheduled_jobs as cron_jobs
from app.models.schemas import (
    GameState, Plan, PlanDay, PushTokenRecord, Task, UserProfile,
)
from app.services import notification_service, push_service
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


def test_midnight_notification_hour_stays_zero():
    from app.storage.supabase_repository import _clock

    assert _clock(0, 8) == 0
    assert _clock(0, 0) == 0
    assert _clock(None, 8) == 8
    assert _clock("", 8) == 8


def test_secret_key_alias(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    cron_jobs._service_key_set()
    assert cron_jobs._service_key_set() is True


def test_close_day_user_failures_are_reported(monkeypatch):
    reported: dict = {}

    def fake_close(repo, deadline_ts=None):
        return {
            "failed_users": 1,
            "results": [],
            "user_errors": [{"user_id": "u1", "error": "db down"}],
            "penalized_tasks": 0,
        }

    monkeypatch.setattr(
        "app.services.task_lifecycle_service.close_due_users", fake_close
    )
    monkeypatch.setattr(
        cron_jobs, "_report",
        lambda exc, **extra: reported.update(msg=str(exc), extra=extra),
    )
    monkeypatch.setenv("CRON_SKIP_PUSH", "true")

    warnings = cron_jobs.run_jobs()

    assert any("işlenemedi" in item for item in warnings)
    assert reported["extra"]["step"] == "close-day"
    assert reported["extra"]["failed_users"] == 1
    assert "db down" in reported["msg"]


def test_notifications_wait_for_next_run_when_budget_is_spent(monkeypatch):
    def fake_close(repo, deadline_ts=None):
        return {
            "failed_users": 0,
            "results": [],
            "user_errors": [],
            "penalized_tasks": 0,
        }

    called = {"notifications": 0}

    def fake_notifications(repo, now_utc=None, deadline_ts=None):
        called["notifications"] += 1
        return {}

    monkeypatch.setattr(
        "app.services.task_lifecycle_service.close_due_users", fake_close
    )
    monkeypatch.setattr(
        "app.services.notification_service.run_due_notifications",
        fake_notifications,
    )
    monkeypatch.setenv("CRON_SKIP_PUSH", "false")
    monkeypatch.setenv("CRON_TIME_BUDGET_SEC", "0")

    warnings = cron_jobs.run_jobs()

    assert called["notifications"] == 0
    assert any("süre bütçesi" in item for item in warnings)


def test_invalid_push_token_does_not_consume_valid_result(monkeypatch):
    repository = InMemoryRepository()
    user_id = "push-align"
    day = date(2026, 7, 11)
    repository.save_profile(
        user_id, UserProfile(timezone="Europe/Istanbul", notif_hour=8, notif_minute=0)
    )
    repository.save_plan(user_id, Plan(
        id="plan-push",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=[Task(
            id="task-push",
            day=1,
            title="Yürü",
            categories=["İrade"],
            date=day,
        )])],
    ))
    repository.upsert_push_token(PushTokenRecord(
        user_id=user_id, token="not-a-token", platform="ios"
    ))
    repository.upsert_push_token(PushTokenRecord(
        user_id=user_id, token="ExpoPushToken[valid]", platform="ios"
    ))
    posted: list = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"status": "ok"}]}

    def fake_post(url, **kwargs):
        posted.append(kwargs["json"])
        return Response()

    monkeypatch.setattr(push_service.httpx, "post", fake_post)
    # 08:00 Istanbul — görev vakti, tarot bir dakika sonra, bonus 15:00'te.
    now = datetime(2026, 7, 11, 5, 0, tzinfo=timezone.utc)
    result = notification_service.run_due_notifications(repository, now)

    assert posted and len(posted[0]) == 1
    assert posted[0][0]["to"] == "ExpoPushToken[valid]"
    assert result["task_reminders_sent"] == 1
    assert repository._push_tokens["ExpoPushToken[valid]"].last_task_reminder_date == day
    assert repository._push_tokens["not-a-token"].last_task_reminder_date is None


def test_penalty_notification_counts_successful_delivery(monkeypatch):
    repository = InMemoryRepository()
    user_id = "penalty-count"
    repository.upsert_push_token(PushTokenRecord(
        user_id=user_id, token="ExpoPushToken[penalty]", platform="ios"
    ))

    def fake_send(messages, timeout=8):
        return [{"status": "ok"} for _ in messages]

    monkeypatch.setattr(push_service, "send_batched", fake_send)
    sent = notification_service.send_penalty_notifications(repository, [{
        "user_id": user_id,
        "penalized_tasks": 1,
        "streak_len": 4,
    }])

    assert sent == 1

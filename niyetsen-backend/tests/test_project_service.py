"""Çoklu plan ve timezone günlük görev kuralları."""
from datetime import date, timedelta

from app.models.schemas import ChatMessage, Plan, PlanDay, Task, UserProfile
from app.services import project_service, task_lifecycle_service
from app.storage.repository import InMemoryRepository


def _task(task_id: str, day: date) -> Task:
    return Task(
        id=task_id,
        day=1,
        title=f"Görev {task_id}",
        categories=["İrade"],
        date=day,
    )


def test_get_today_tasks_collects_from_all_plans() -> None:
    repo = InMemoryRepository()
    user_id = "all-plans"
    day = date(2026, 7, 11)
    plan_a = Plan(
        id="plan-a",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=[_task("a-task", day)])],
        name="Plan A",
        slot_no=1,
    )
    plan_b = Plan(
        id="plan-b",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=[_task("b-task", day)])],
        name="Plan B",
        slot_no=2,
    )
    repo.save_plan(user_id, plan_a)
    repo._user_plans(user_id)[plan_b.id] = plan_b
    repo._user_meta(user_id)[plan_b.id] = {"name": "Plan B", "slot_no": 2}

    items = project_service.get_today_tasks(repo, user_id, today=day)
    assert {item.task.id for item in items} == {"a-task", "b-task"}


def test_get_today_tasks_uses_profile_timezone_when_today_omitted(monkeypatch) -> None:
    repo = InMemoryRepository()
    user_id = "tz-user"
    repo.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    local_day = date(2026, 7, 11)
    repo.save_plan(
        user_id,
        Plan(
            id="tz-plan",
            duration_days=1,
            batch_generated_until=1,
            start_date=local_day,
            days=[PlanDay(day=1, tasks=[_task("tz-task", local_day)])],
        ),
    )

    monkeypatch.setattr(
        project_service,
        "_user_local_today",
        lambda _tz: local_day,
    )
    items = project_service.get_today_tasks(repo, user_id)
    assert len(items) == 1
    assert items[0].task.id == "tz-task"


def test_close_user_day_penalizes_tasks_from_all_plans() -> None:
    repository = InMemoryRepository()
    user_id = "multi-plan-user"
    day = date(2026, 7, 11)
    plan_a = Plan(
        id="plan-a",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=[_task("a-task", day)])],
        name="Plan A",
        slot_no=1,
    )
    plan_b = Plan(
        id="plan-b",
        duration_days=1,
        batch_generated_until=1,
        start_date=day,
        days=[PlanDay(day=1, tasks=[_task("b-task", day)])],
        name="Plan B",
        slot_no=2,
    )
    repository.save_plan(user_id, plan_a)
    repository._user_plans(user_id)[plan_b.id] = plan_b
    repository._user_meta(user_id)[plan_b.id] = {"name": "Plan B", "slot_no": 2}

    result = task_lifecycle_service.close_user_day(repository, user_id, day)
    assert result["penalized_tasks"] == 2
    assert repository.get_task(user_id, "a-task").status == "missed_silent"
    assert repository.get_task(user_id, "b-task").status == "missed_silent"


def test_start_new_project_opens_fresh_chat_thread() -> None:
    repo = InMemoryRepository()
    user_id = "new-project-chat"
    repo.append_chat_message(
        user_id,
        ChatMessage(role="user", content="eski test yazısı"),
    )
    before = repo.list_chat_threads(user_id)
    assert before
    summary = project_service.start_new_project(repo, user_id)
    assert summary.has_content is False
    threads = repo.list_chat_threads(user_id)
    active = next(t for t in threads if t.is_active)
    assert repo.get_chat_history(user_id) == []
    assert active.id != before[0].id


def test_daily_tasks_response_flags_extension_when_batch_lags() -> None:
    repo = InMemoryRepository()
    user_id = "lag-batch"
    start = date(2026, 7, 20)
    today = start + timedelta(days=10)  # plan günü 11; batch yalnız 7
    repo.save_plan(
        user_id,
        Plan(
            id="lag-plan",
            duration_days=180,
            batch_generated_until=7,
            start_date=start,
            days=[PlanDay(day=1, tasks=[_task("d1", start)])],
            name="Entellektüel",
        ),
    )
    resp = project_service.get_daily_tasks_response(repo, user_id, today=today)
    assert resp.has_active_plan is True
    assert resp.needs_extension is True
    assert resp.plan_day == 11
    assert resp.batch_generated_until == 7
    assert resp.items == []

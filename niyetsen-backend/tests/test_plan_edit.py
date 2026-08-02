"""FAZ 8.3 — plan görev düzenleme (PATCH/POST/DELETE), Gemini yok."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Plan, PlanDay, Task
from app.services import plan_edit_service, task_lifecycle_service
from app.storage.repository import InMemoryRepository

client = TestClient(app)

USER = "plan-edit-user"
START = date(2026, 8, 2)


def _headers(user_id: str = USER) -> dict[str, str]:
    return {"X-User-Id": user_id}


def _seed_plan(repo: InMemoryRepository, *, status: str = "pending") -> Plan:
    plan = Plan(
        id="plan-edit-1",
        duration_days=30,
        batch_generated_until=7,
        start_date=START,
        days=[
            PlanDay(
                day=1,
                theme="Başlangıç",
                tasks=[
                    Task(
                        id="task-a",
                        day=1,
                        date=START,
                        title="Sabah yürüyüşü",
                        categories=["İrade"],
                        status=status,  # type: ignore[arg-type]
                    ),
                    Task(
                        id="task-b",
                        day=1,
                        date=START,
                        title="Su iç",
                        categories=["İstikrar"],
                        status="pending",
                    ),
                ],
            ),
            PlanDay(
                day=2,
                theme="Devam",
                tasks=[
                    Task(
                        id="task-c",
                        day=2,
                        date=START + timedelta(days=1),
                        title="Kitap oku",
                        categories=["Disiplin"],
                        status="pending",
                    ),
                ],
            ),
        ],
        name="Test Plan",
    )
    repo.save_plan(USER, plan)
    return plan


def test_patch_task_title(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    res = client.patch(
        "/plan/tasks/task-a",
        headers=_headers(),
        json={"title": "Akşam yürüyüşü"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Akşam yürüyüşü"
    assert body["date"] == START.isoformat()
    assert isolated_in_memory_repo.get_task(USER, "task-a").title == "Akşam yürüyüşü"


def test_patch_task_move_date(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    tomorrow = START + timedelta(days=1)
    task = plan_edit_service.edit_task(
        isolated_in_memory_repo,
        USER,
        "task-a",
        new_date=tomorrow,
        today=START,
    )
    assert task.date == tomorrow
    assert task.day == 2
    plan = isolated_in_memory_repo.get_plan(USER)
    day1 = next(d for d in plan.days if d.day == 1)
    assert [t.id for t in day1.tasks] == ["task-b"]
    day2 = next(d for d in plan.days if d.day == 2)
    assert "task-a" in [t.id for t in day2.tasks]


def test_patch_rejects_past_date(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    with pytest.raises(plan_edit_service.PlanEditError, match="Geçmiş"):
        plan_edit_service.edit_task(
            isolated_in_memory_repo,
            USER,
            "task-a",
            new_date=START - timedelta(days=1),
            today=START,
        )


def test_patch_rejects_done_task(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo, status="done")
    res = client.patch(
        "/plan/tasks/task-a",
        headers=_headers(),
        json={"title": "Yeni ad"},
    )
    assert res.status_code == 409


def test_patch_unknown_task_404(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    res = client.patch(
        "/plan/tasks/missing",
        headers=_headers(),
        json={"title": "X"},
    )
    assert res.status_code == 404


def test_post_add_task(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    target = START + timedelta(days=2)
    task = plan_edit_service.add_task(
        isolated_in_memory_repo,
        USER,
        target,
        title="Yeni alışkanlık",
        categories=["Özgüven"],
        today=START,
    )
    assert task.title == "Yeni alışkanlık"
    assert task.date == target
    assert task.day == 3
    assert task.status == "pending"
    assert isolated_in_memory_repo.get_task(USER, task.id) is not None


def test_post_add_task_http(isolated_in_memory_repo: InMemoryRepository):
    today = date.today()
    plan = Plan(
        id="plan-http",
        duration_days=30,
        batch_generated_until=7,
        start_date=today,
        days=[
            PlanDay(
                day=1,
                tasks=[
                    Task(
                        id="t1",
                        day=1,
                        date=today,
                        title="A",
                        categories=["İrade"],
                    )
                ],
            )
        ],
    )
    isolated_in_memory_repo.save_plan(USER, plan)
    target = today + timedelta(days=1)
    res = client.post(
        f"/plan/days/{target.isoformat()}/tasks",
        headers=_headers(),
        json={"title": "HTTP eklenen", "categories": ["Sosyallik"]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "HTTP eklenen"
    assert body["date"] == target.isoformat()
    assert body["categories"] == ["Sosyallik"]


def test_post_rejects_past_date_http(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    past = (date.today() - timedelta(days=3)).isoformat()
    res = client.post(
        f"/plan/days/{past}/tasks",
        headers=_headers(),
        json={"title": "Geçmiş görev"},
    )
    assert res.status_code == 422
    assert "Geçmiş" in res.json()["detail"]


def test_delete_pending_no_penalty(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    state = isolated_in_memory_repo.get_state(USER)
    state.points["İrade"] = 100
    isolated_in_memory_repo.save_state(state)

    res = client.delete("/plan/tasks/task-a", headers=_headers())
    assert res.status_code == 204
    assert isolated_in_memory_repo.get_task(USER, "task-a") is None
    assert isolated_in_memory_repo.get_state(USER).points["İrade"] == 100


def test_delete_done_rejected(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo, status="done")
    res = client.delete("/plan/tasks/task-a", headers=_headers())
    assert res.status_code == 409
    assert isolated_in_memory_repo.get_task(USER, "task-a") is not None


def test_delete_unknown_404(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    res = client.delete("/plan/tasks/nope", headers=_headers())
    assert res.status_code == 404


def test_ownership_other_user_404(isolated_in_memory_repo: InMemoryRepository):
    _seed_plan(isolated_in_memory_repo)
    res = client.patch(
        "/plan/tasks/task-a",
        headers=_headers("other-user"),
        json={"title": "Hırsız"},
    )
    assert res.status_code == 404


def test_cron_unaffected_after_move(isolated_in_memory_repo: InMemoryRepository):
    """Taşınan görev eski günde kalmamalı; cron o günü cezalandırmaz."""
    _seed_plan(isolated_in_memory_repo)
    tomorrow = START + timedelta(days=1)
    plan_edit_service.edit_task(
        isolated_in_memory_repo,
        USER,
        "task-a",
        new_date=tomorrow,
        today=START,
    )
    result = task_lifecycle_service.close_user_day(
        isolated_in_memory_repo, USER, START
    )
    assert result["penalized_tasks"] == 1
    assert isolated_in_memory_repo.get_task(USER, "task-a").status == "pending"
    assert isolated_in_memory_repo.get_task(USER, "task-b").status == "missed_silent"

"""Kart alt adımları puan yazmaz ve başka kullanıcının görevine dokunmaz."""
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Plan, PlanDay, Task, UserProfile
from app.storage.repository import repo

client = TestClient(app)


def _seed(user_id: str, task_id: str = "kart-1") -> None:
    repo.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    today = date(2026, 9, 22)
    repo.save_plan(
        user_id,
        Plan(
            id=f"plan-{user_id}",
            duration_days=365,
            batch_generated_until=7,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    theme="Kahvaltı",
                    tasks=[
                        Task(
                            id=task_id,
                            day=1,
                            date=today,
                            title="Yulaf ezmesi",
                            categories=["İstikrar", "Özsaygı"],
                        )
                    ],
                )
            ],
        ),
    )


def test_steps_roundtrip_and_isolation() -> None:
    _seed("steps-owner", "kart-1")
    _seed("steps-other", "baska")
    before = repo.get_state("steps-owner").points["İstikrar"]
    created = client.put(
        "/plan/tasks/kart-1/steps",
        headers={"X-User-Id": "steps-owner"},
        json={"steps": [
            {"id": "", "title": "  Blog listesi çıkar  ", "done": False},
            {"title": "3 tarif seç", "done": True},
        ]},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["steps"][0]["title"] == "Blog listesi çıkar"
    assert body["steps"][0]["order"] == 0
    assert body["steps"][1]["done"] is True
    assert repo.get_state("steps-owner").points["İstikrar"] == before

    listed = client.get("/plan/tasks/kart-1/steps", headers={"X-User-Id": "steps-owner"})
    assert listed.status_code == 200
    assert len(listed.json()["steps"]) == 2

    stolen = client.get("/plan/tasks/kart-1/steps", headers={"X-User-Id": "steps-other"})
    assert stolen.status_code == 404


def test_steps_reject_empty_title() -> None:
    _seed("steps-empty", "kart-2")
    resp = client.put(
        "/plan/tasks/kart-2/steps",
        headers={"X-User-Id": "steps-empty"},
        json={"steps": [{"title": "   "}]},
    )
    assert resp.status_code == 422

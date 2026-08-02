"""Çoklu plan projeleri — free=1 plan, abonelikle yeni niyet."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import plan_service
from tests.conftest import grant_chat_consent

client = TestClient(app)

FAKE_PLAN_JSON = {
    "days": [
        {
            "day": 1,
            "theme": "Başlangıç",
            "tasks": [
                {
                    "title": "Görev 1",
                    "task_type": "alışkanlık",
                    "categories": ["İstikrar"],
                    "image_keyword": "morning walk",
                    "duration_min": 10,
                    "tiny_version": "2 dk başla.",
                },
            ],
        },
    ]
}


@pytest.fixture(autouse=True)
def _mock_plan_gemini(monkeypatch):
    async def fake_generate_json(*args, **kwargs):
        return FAKE_PLAN_JSON

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)


def _headers(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}


def test_free_user_blocked_from_second_project():
    user_id = "multi-plan-free-user"
    first = client.post("/projects/new", headers=_headers(user_id))
    assert first.status_code == 200

    collected = {
        "city": "İstanbul",
        "interests": ["kitap"],
        "weekly_hours": 5,
        "duration_days": 7,
    }
    grant_chat_consent(user_id, client)
    generate = client.post(
        "/plan/generate",
        headers=_headers(user_id),
        json={"collected": collected, "duration_days": 7},
    )
    assert generate.status_code == 200

    second = client.post("/projects/new", headers=_headers(user_id))
    assert second.status_code == 402
    assert second.json()["detail"]["code"] == "paywall_required"


def test_premium_user_can_start_second_project():
    user_id = "multi-plan-premium-user"
    client.post("/projects/new", headers=_headers(user_id))
    collected = {
        "city": "Ankara",
        "interests": ["spor"],
        "weekly_hours": 4,
        "duration_days": 7,
    }
    grant_chat_consent(user_id, client)
    client.post(
        "/plan/generate",
        headers=_headers(user_id),
        json={"collected": collected, "duration_days": 7},
    )

    from app.storage.repository import repo

    repo.update_subscription(user_id, subscription_status="active")

    second = client.post("/projects/new", headers=_headers(user_id))
    assert second.status_code == 200
    body = second.json()
    assert body["slot_no"] == 2
    assert body["is_active"] is True

    projects = client.get("/projects", headers=_headers(user_id)).json()
    assert len(projects) == 2


def test_premium_user_unlimited_plan_slots():
    """Abone: 2'lik tavan YOK — Plan 3+ de açılır (MASTER_PLAN §1.1.1)."""
    user_id = "multi-plan-premium-unlimited"
    from app.storage.repository import repo

    repo.update_subscription(user_id, subscription_status="active")
    grant_chat_consent(user_id, client)

    first = client.post("/projects/new", headers=_headers(user_id))
    assert first.status_code == 200
    collected = {
        "city": "İzmir",
        "interests": ["yoga"],
        "weekly_hours": 3,
        "duration_days": 7,
    }
    assert (
        client.post(
            "/plan/generate",
            headers=_headers(user_id),
            json={"collected": collected, "duration_days": 7},
        ).status_code
        == 200
    )

    second = client.post("/projects/new", headers=_headers(user_id))
    assert second.status_code == 200
    assert second.json()["slot_no"] == 2

    third = client.post("/projects/new", headers=_headers(user_id))
    assert third.status_code == 200
    assert third.json()["slot_no"] == 3
    assert third.json()["is_active"] is True

    projects = client.get("/projects", headers=_headers(user_id)).json()
    assert len(projects) == 3
    assert {p["slot_no"] for p in projects} == {1, 2, 3}


def test_rename_and_activate_project():
    user_id = "multi-plan-rename-user"
    client.post("/projects/new", headers=_headers(user_id))
    projects = client.get("/projects", headers=_headers(user_id)).json()
    plan_id = projects[0]["id"]

    renamed = client.patch(
        f"/projects/{plan_id}",
        headers=_headers(user_id),
        json={"name": "Sağlıklı Hayat"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Sağlıklı Hayat"

    from app.storage.repository import repo

    repo.update_subscription(user_id, subscription_status="active")
    second = client.post("/projects/new", headers=_headers(user_id)).json()
    activated = client.put(
        f"/projects/{plan_id}/activate",
        headers=_headers(user_id),
    )
    assert activated.status_code == 200
    assert activated.json()["id"] == plan_id
    assert activated.json()["is_active"] is True
    assert second["id"] != plan_id


def test_two_plan_switch_certification_five_times():
    """FAZ 8.1/8.5 KAPI: iki plan arasında tekrarlı geçiş — aktif plan,
    günün görevleri ve vision-board görselleri karışmaz."""
    user_id = "multi-plan-switch-cert"
    from app.storage.repository import repo

    repo.update_subscription(user_id, subscription_status="active")
    grant_chat_consent(user_id, client)

    # Plan A — entelektüel
    assert client.post("/projects/new", headers=_headers(user_id)).status_code == 200
    plan_a = client.post(
        "/plan/generate",
        headers=_headers(user_id),
        json={
            "collected": {
                "city": "İstanbul",
                "interests": ["kitap", "felsefe"],
                "weekly_hours": 6,
                "duration_days": 7,
            },
            "duration_days": 7,
        },
    )
    assert plan_a.status_code == 200
    plan_a_id = plan_a.json()["id"]
    client.patch(
        f"/projects/{plan_a_id}",
        headers=_headers(user_id),
        json={"name": "Entelektüel"},
    )

    # Plan B — sporcu (yeni slot + generate)
    assert client.post("/projects/new", headers=_headers(user_id)).status_code == 200
    plan_b = client.post(
        "/plan/generate",
        headers=_headers(user_id),
        json={
            "collected": {
                "city": "Ankara",
                "interests": ["koşu", "spor"],
                "weekly_hours": 8,
                "duration_days": 7,
            },
            "duration_days": 7,
        },
    )
    assert plan_b.status_code == 200
    plan_b_id = plan_b.json()["id"]
    client.patch(
        f"/projects/{plan_b_id}",
        headers=_headers(user_id),
        json={"name": "Sporcu"},
    )

    assert plan_a_id != plan_b_id
    projects = client.get("/projects", headers=_headers(user_id)).json()
    assert len(projects) == 2

    # Her planda en az 1 görev + image_url (vision board sinyali)
    for plan_id in (plan_a_id, plan_b_id):
        client.put(
            f"/projects/{plan_id}/activate",
            headers=_headers(user_id),
        )
        plan = client.get("/plan", headers=_headers(user_id)).json()
        assert plan["id"] == plan_id
        tasks = [
            t for day in plan["days"] for t in day.get("tasks", [])
        ]
        assert tasks, f"plan {plan_id} boş"
        assert any(t.get("image_url") or t.get("image_keyword") for t in tasks)

    # 5 ardışık geçiş: A→B→A→B→A — aktif plan / vision board sızması yok.
    # Not: /tasks/daily TÜM planların bugünkü görevlerini birleştirir
    # (çoklu niyet UX); aktiflik filtresi GET /plan üzerindedir.
    sequence = [plan_a_id, plan_b_id, plan_a_id, plan_b_id, plan_a_id]
    for expected_id in sequence:
        activated = client.put(
            f"/projects/{expected_id}/activate",
            headers=_headers(user_id),
        )
        assert activated.status_code == 200
        assert activated.json()["id"] == expected_id
        assert activated.json()["is_active"] is True

        current = client.get("/plan", headers=_headers(user_id)).json()
        assert current["id"] == expected_id
        assert current["days"], "aktif plan vision board boş olmamalı"

        listing = client.get("/projects", headers=_headers(user_id)).json()
        active = [p for p in listing if p["is_active"]]
        assert len(active) == 1
        assert active[0]["id"] == expected_id

        daily = client.get("/tasks/daily", headers=_headers(user_id))
        assert daily.status_code == 200
        daily_body = daily.json()
        daily_items = daily_body.get("items", daily_body if isinstance(daily_body, list) else [])
        daily_plan_ids = {item["plan_id"] for item in daily_items}
        # Bugün her iki planda da görev varsa ikisi de listede olabilir;
        # aktif planın görevleri mutlaka gelsin.
        assert expected_id in daily_plan_ids or not any(
            day.get("tasks") for day in current["days"]
            if any(t.get("date") for t in day.get("tasks", []))
        )

"""Çoklu plan projeleri — free=1 plan, abonelikle yeni niyet."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ConsentChoice, ConsentUpdate
from app.services import consent_service, plan_service
from app.storage.repository import repo

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


def _ensure_consent(user_id: str) -> None:
    consent_service.update(
        repo,
        user_id,
        ConsentUpdate(
            privacy_policy=ConsentChoice(accepted=True),
            kvkk_explicit_consent=ConsentChoice(accepted=True),
            ai_chat_processing=ConsentChoice(accepted=True),
        ),
    )


def test_free_user_blocked_from_second_project():
    user_id = "multi-plan-free-user"
    _ensure_consent(user_id)
    first = client.post("/projects/new", headers=_headers(user_id))
    assert first.status_code == 200

    collected = {
        "city": "İstanbul",
        "interests": ["kitap"],
        "weekly_hours": 5,
        "duration_days": 7,
    }
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
    _ensure_consent(user_id)
    client.post("/projects/new", headers=_headers(user_id))
    collected = {
        "city": "Ankara",
        "interests": ["spor"],
        "weekly_hours": 4,
        "duration_days": 7,
    }
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

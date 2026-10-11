"""
Niyetsen — Plan Tarihleri + Gün Sonu Cron Entegrasyon Testi
Bug #1 regresyon testi: Task.date artık plan_service'te hesaplanıyor, bu yüzden
/cron/close-day artık SADECE 1. gün için değil, her gün için doğru çalışmalı.
Gemini çağrısı mock'lanır — gerçek API anahtarı gerekmez.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services import plan_service
from app.storage.repository import repo
from tests.conftest import grant_chat_consent

client = TestClient(app)

FAKE_PLAN_JSON = {
    "days": [
        {"day": 1, "theme": "Başlangıç", "tasks": [
            {"title": "Görev 1", "task_type": "alışkanlık", "categories": ["İstikrar"],
             "image_keyword": "test", "duration_min": 10, "tiny_version": "2 dk başla."},
        ]},
        {"day": 2, "theme": "Devam", "tasks": [
            {"title": "Görev 2", "task_type": "alışkanlık", "categories": ["Disiplin"],
             "image_keyword": "test", "duration_min": 10, "tiny_version": "2 dk başla."},
        ]},
        {"day": 3, "theme": "Son", "tasks": [
            {"title": "Görev 3", "task_type": "alışkanlık", "categories": ["İrade"],
             "image_keyword": "test", "duration_min": 10, "tiny_version": "2 dk başla."},
        ]},
    ]
}

COLLECTED = {"city": "İstanbul", "interests": ["spor"], "weekly_hours": 5}


@pytest.fixture(autouse=True)
def _mock_gemini(monkeypatch):
    """plan_service.generate_json'ı sahte, sabit bir plan JSON'uyla değiştir."""
    async def fake_generate_json(*args, **kwargs):
        return FAKE_PLAN_JSON

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)
    monkeypatch.setattr(settings, "CRON_SECRET", "test-cron-secret")


def _generate_plan(user_id: str) -> dict:
    grant_chat_consent(user_id, client)
    resp = client.post(
        "/plan/generate",
        json={"collected": COLLECTED, "duration_days": 3},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    return resp.json()


def test_generate_batch_survives_dirty_model_payload(monkeypatch):
    """Bozuk süre/kategori veya dict olmayan gün tüm plan kaydını düşürmesin."""
    import asyncio

    from app.models.schemas import CollectedIntent
    from app.services.image_service import ImageResult

    captured: dict = {}

    async def fake_json(*_args, **_kwargs):
        return {
            "days": [
                "bozuk-gun",
                {
                    "theme": "İkinci",
                    "tasks": [
                        "bozuk-gorev",
                        {
                            "title": "Yürü",
                            "categories": "Disiplin",
                            "duration_min": "yirmi dakika",
                            "image_keyword": "walk",
                        },
                        {
                            "title": "Oku",
                            "categories": ["Disiplin", "Disiplin", "İrade"],
                            "duration_min": 20,
                            "image_keyword": "read",
                        },
                    ],
                },
            ]
        }

    async def fake_enrich(items, *, city, interests):
        captured["city"] = city
        captured["interests"] = list(interests)
        return [keyword for _title, keyword, _cats in items]

    async def fake_image(_keyword, **kwargs):
        captured["allow_gemini"] = kwargs.get("allow_gemini")
        captured["image_city"] = kwargs.get("city")
        return ImageResult(url="https://example.com/a.jpg", source="unsplash")

    monkeypatch.setattr(plan_service, "generate_json", fake_json)
    monkeypatch.setattr(plan_service, "enrich_image_keywords_batch", fake_enrich)
    monkeypatch.setattr(plan_service, "get_image_async", fake_image)

    plan = asyncio.run(
        plan_service.generate_batch(
            CollectedIntent(),
            duration_days=7,
            start_date=date(2026, 8, 1),
        )
    )
    by_title = {
        task.title: task
        for day in plan.days
        for task in day.tasks
    }
    assert set(by_title) == {"Yürü", "Oku"}
    assert by_title["Yürü"].categories == ["Disiplin"]
    assert by_title["Yürü"].duration_min == 15
    assert by_title["Oku"].categories == ["Disiplin", "İrade"]
    assert captured["city"] == ""
    assert captured["interests"] == []
    assert captured["image_city"] == ""
    assert captured["allow_gemini"] is False
    assert "belirtilmedi" not in by_title["Yürü"].image_keyword


def test_get_plan_returns_404_when_none_exists():
    resp = client.get("/plan", headers={"X-User-Id": "no_plan_user"})
    assert resp.status_code == 404


def test_get_plan_returns_existing_plan_without_regenerating():
    user_id = "get_plan_user"
    generated = _generate_plan(user_id)

    fetched = client.get("/plan", headers={"X-User-Id": user_id})
    assert fetched.status_code == 200
    assert fetched.json()["id"] == generated["id"]
    assert fetched.json()["start_date"] == generated["start_date"]


def test_plan_tasks_get_correct_calendar_dates():
    plan = _generate_plan("cron_date_user")
    start = date.fromisoformat(plan["start_date"])
    days = {d["day"]: d for d in plan["days"]}

    assert days[1]["tasks"][0]["date"] == start.isoformat()
    assert days[2]["tasks"][0]["date"] == (start + timedelta(days=1)).isoformat()
    assert days[3]["tasks"][0]["date"] == (start + timedelta(days=2)).isoformat()


def test_cron_close_day_penalizes_day_two_task_not_just_day_one():
    """
    Bug #1 öncesi: gün 2/3 görevlerinin date'i None olduğu için cron SADECE
    gün 1'i işleyebiliyordu. Bu test gün 2'nin tarihiyle cron'u tetikleyip
    SADECE o günün görevinin cezalandırıldığını, diğerlerinin dokunulmadığını
    doğrular.
    """
    user_id = "cron_day2_user"
    plan = _generate_plan(user_id)
    start = date.fromisoformat(plan["start_date"])
    day2_date = start + timedelta(days=1)

    days = {d["day"]: d for d in plan["days"]}
    task1_id = days[1]["tasks"][0]["id"]
    task2_id = days[2]["tasks"][0]["id"]
    task3_id = days[3]["tasks"][0]["id"]

    cron_resp = client.post(
        "/cron/close-day",
        params={"at": datetime.combine(
            day2_date, time(20, 59), tzinfo=timezone.utc
        ).isoformat()},
        headers={"X-Cron-Secret": "test-cron-secret"},
    )
    assert cron_resp.status_code == 200
    body = cron_resp.json()
    user_result = next(row for row in body["results"] if row["user_id"] == user_id)
    assert user_result["penalized_tasks"] == 1  # sadece gün 2'nin görevi

    # Gün 2'nin görevi cezalandı (sessiz kaçırma), diğer günler dokunulmadı.
    assert repo.get_task(user_id, task2_id).status == "missed_silent"
    assert repo.get_task(user_id, task1_id).status == "pending"
    assert repo.get_task(user_id, task3_id).status == "pending"

    state = client.get("/me/state", headers={"X-User-Id": user_id}).json()
    assert state["silent_miss_streak"] == 1


def test_cron_close_day_then_day_three_penalizes_only_that_day():
    """Aynı akışı 3. gün için tekrar et — cron her gün için genel olarak çalışmalı."""
    user_id = "cron_day3_user"
    plan = _generate_plan(user_id)
    start = date.fromisoformat(plan["start_date"])
    day3_date = start + timedelta(days=2)

    days = {d["day"]: d for d in plan["days"]}
    task1_id = days[1]["tasks"][0]["id"]
    task3_id = days[3]["tasks"][0]["id"]

    cron_resp = client.post(
        "/cron/close-day",
        params={"at": datetime.combine(
            day3_date, time(20, 59), tzinfo=timezone.utc
        ).isoformat()},
        headers={"X-Cron-Secret": "test-cron-secret"},
    )
    assert cron_resp.status_code == 200
    user_result = next(
        row for row in cron_resp.json()["results"] if row["user_id"] == user_id
    )
    assert user_result["penalized_tasks"] == 1

    assert repo.get_task(user_id, task3_id).status == "missed_silent"
    assert repo.get_task(user_id, task1_id).status == "pending"  # gün 1'e dokunulmadı

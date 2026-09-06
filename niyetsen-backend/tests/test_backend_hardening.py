"""Canlı 500'lerin kök nedenleri: timestamptz str, jsonb dict, slot yarışı."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.core.datetimes import coerce_date, coerce_datetime, local_today
from app.main import app
from app.models.schemas import Plan, PlanDay, Task, UserProfile
from app.services import intent_service, plan_service
from app.storage.db_coerce import is_unique_violation, parse_json_object
from app.storage.repository import repo
from app.storage.supabase_repository import _parse_optional_date
from tests.conftest import grant_chat_consent

client = TestClient(app)


def test_coerce_datetime_accepts_z_and_naive() -> None:
    zulu = coerce_datetime("2026-08-10T08:00:00Z")
    assert zulu is not None and zulu.tzinfo is not None
    naive = coerce_datetime(datetime(2026, 8, 10, 8, 0))
    assert naive is not None and naive.tzinfo is timezone.utc
    assert coerce_datetime(None) is None
    assert coerce_datetime("not-a-date") is None
    as_date = coerce_datetime(date(2026, 8, 10))
    assert as_date == datetime(2026, 8, 10, tzinfo=timezone.utc)


def test_parse_json_object_accepts_dict_and_string() -> None:
    """jsonb PostgREST'ten dict gelir; json.loads(dict) TypeError atıyordu."""
    assert parse_json_object({"cards": [{"name": "Yıldız"}]})["cards"][0]["name"] == "Yıldız"
    assert parse_json_object('{"interpretation": "ayna"}')["interpretation"] == "ayna"
    assert parse_json_object(None) == {}
    assert parse_json_object([1, 2]) == {}


def test_unique_violation_detects_postgres_23505() -> None:
    class Fake(Exception):
        code = "23505"

    assert is_unique_violation(Fake("duplicate"))
    assert is_unique_violation(
        Exception('duplicate key value violates unique constraint "plans_user_slot_idx"')
    )
    assert not is_unique_violation(Exception("connection reset"))


def test_duplicate_slot_create_is_idempotent_and_session_ok() -> None:
    user = "slot-race-user"
    first = repo.create_draft_plan(user, name="Plan 1", slot_no=1)
    second = repo.create_draft_plan(user, name="Plan 1", slot_no=1)
    assert first == second
    res = client.get("/chat/session", headers={"X-User-Id": user})
    assert res.status_code == 200
    assert res.json()["active_plan_name"]


def test_coerce_date_accepts_timestamptz_and_datetime_subclass() -> None:
    """PostgREST date kolonu bazen timestamptz str / datetime verir — fromisoformat 500."""
    assert coerce_date("2026-08-10") == date(2026, 8, 10)
    assert coerce_date("2026-08-10T00:00:00+00:00") == date(2026, 8, 10)
    assert coerce_date("2026-08-10T08:00:00Z") == date(2026, 8, 10)
    assert coerce_date(datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)) == date(2026, 8, 10)
    assert coerce_date(date(2026, 8, 10)) == date(2026, 8, 10)
    assert coerce_date(None) is None
    assert coerce_date("not-a-date") is None


def test_parse_optional_date_datetime_becomes_date() -> None:
    dt = datetime(2026, 8, 10, 15, 30, tzinfo=timezone.utc)
    parsed = _parse_optional_date(dt)
    assert parsed == date(2026, 8, 10)
    assert type(parsed) is date
    assert _parse_optional_date("2026-08-10T00:00:00+00:00") == date(2026, 8, 10)
    assert _parse_optional_date("2026-08-10T08:00:00Z") == date(2026, 8, 10)
    assert _parse_optional_date("not-a-date") is None


def test_local_today_follows_named_zone() -> None:
    # Eylül'de LA = PDT (UTC−7). 06:00 UTC = 23:00 önceki gün.
    utc_before_la_midnight = datetime(2026, 9, 7, 6, 0, tzinfo=timezone.utc)
    assert local_today("America/Los_Angeles", now=utc_before_la_midnight) == date(2026, 9, 6)
    assert local_today("Europe/Istanbul", now=utc_before_la_midnight) == date(2026, 9, 7)
    assert local_today("Gezegen/Yok", now=utc_before_la_midnight) == date(2026, 9, 7)


def test_plan_generate_start_date_follows_profile_timezone(monkeypatch) -> None:
    async def fake_generate_json(*args, **kwargs):
        return {
            "days": [
                {
                    "day": 1,
                    "theme": "Başlangıç",
                    "tasks": [
                        {
                            "title": "Su iç",
                            "task_type": "alışkanlık",
                            "categories": ["İstikrar"],
                            "image_keyword": "water",
                            "duration_min": 5,
                            "tiny_version": "Bir yudum.",
                        }
                    ],
                }
            ]
        }

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)
    monkeypatch.setattr("app.api.routes._user_today", lambda tz: date(2026, 8, 20))
    user = "tz-plan-user"
    repo.save_profile(user, UserProfile(timezone="America/Los_Angeles"))
    grant_chat_consent(user, client)
    resp = client.post(
        "/plan/generate",
        json={"collected": {"city": "LA", "interests": ["spor"], "weekly_hours": 5}, "duration_days": 7},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    assert resp.json()["start_date"] == "2026-08-20"


def test_plan_next_and_ensure_today_empty_model_is_422_not_500(monkeypatch) -> None:
    async def empty_batch(*args, **kwargs):
        raise ValueError("Model boş plan döndürdü — prompt veya niyet verisini kontrol et.")

    monkeypatch.setattr(plan_service, "generate_batch", empty_batch)
    user = "empty-batch-user"
    today = date(2026, 8, 1)
    repo.save_profile(user, UserProfile(timezone="Europe/Istanbul"))
    repo.save_plan(
        user,
        Plan(
            id="empty-batch-plan",
            duration_days=30,
            batch_generated_until=1,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    tasks=[
                        Task(
                            id="keep",
                            day=1,
                            date=today,
                            title="Su iç",
                            categories=["İstikrar"],
                        )
                    ],
                )
            ],
        ),
    )
    next_resp = client.post("/plan/next", json={}, headers={"X-User-Id": user})
    ensure_resp = client.post("/plan/ensure-today", headers={"X-User-Id": user})
    assert next_resp.status_code == 422
    assert ensure_resp.status_code == 422
    assert "boş plan" in next_resp.json()["detail"]


def test_chat_rejects_empty_or_assistant_only_messages() -> None:
    user = "empty-chat-user"
    grant_chat_consent(user, client)
    empty = client.post(
        "/chat", json={"messages": [], "collected": {}}, headers={"X-User-Id": user},
    )
    assistant_only = client.post(
        "/chat",
        json={"messages": [{"role": "assistant", "content": "Merhaba 🌙"}], "collected": {}},
        headers={"X-User-Id": user},
    )
    assert empty.status_code == 400
    assert assistant_only.status_code == 400


def test_chat_history_save_failure_does_not_drop_reply(monkeypatch) -> None:
    async def fake_generate_json(*args, **kwargs):
        return {"reply": "Hangi şehirdesin?", "ready_for_plan": False, "collected": {}}

    def boom(*args, **kwargs):
        raise RuntimeError("chat_messages yazılamadı")

    monkeypatch.setattr(intent_service, "generate_json", fake_generate_json)
    monkeypatch.setattr(repo, "append_chat_messages", boom)
    user = "chat-persist-degrade"
    grant_chat_consent(user, client)
    resp = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "İstanbul'dayım"}], "collected": {}},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    assert "şehir" in resp.json()["reply"]


def test_recap_period_end_follows_user_timezone(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes._user_today", lambda tz: date(2026, 8, 15))
    user = "tz-recap-user"
    repo.save_profile(user, UserProfile(timezone="America/Los_Angeles"))
    resp = client.get("/me/recap?period=7d", headers={"X-User-Id": user})
    assert resp.status_code == 200
    assert resp.json()["end_date"] == "2026-08-15"


def test_plan_edit_today_follows_user_timezone(monkeypatch) -> None:
    """Kullanıcı TZ'sinde bugün, sunucu UTC'sinde dün — ekleme 'geçmiş' sayılmamalı."""
    monkeypatch.setattr("app.api.routes._user_today", lambda tz: date(2026, 8, 20))
    user = "tz-edit-user"
    repo.save_profile(user, UserProfile(timezone="America/Los_Angeles"))
    repo.save_plan(
        user,
        Plan(
            id="tz-edit-plan",
            duration_days=30,
            batch_generated_until=7,
            start_date=date(2026, 8, 15),
            days=[
                PlanDay(
                    day=1,
                    tasks=[
                        Task(
                            id="existing",
                            day=1,
                            date=date(2026, 8, 15),
                            title="Su iç",
                            categories=["İstikrar"],
                        )
                    ],
                )
            ],
        ),
    )
    resp = client.post(
        "/plan/days/2026-08-20/tasks",
        json={"title": "Akşam yürüyüşü", "categories": ["İrade"]},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    assert resp.json()["date"] == "2026-08-20"


def test_plan_generate_rejects_out_of_range_duration() -> None:
    user = "duration-bounds-user"
    grant_chat_consent(user, client)
    zero = client.post(
        "/plan/generate",
        json={"collected": {"city": "İstanbul", "interests": ["spor"], "weekly_hours": 5}, "duration_days": 0},
        headers={"X-User-Id": user},
    )
    huge = client.post(
        "/plan/generate",
        json={"collected": {"city": "İstanbul", "interests": ["spor"], "weekly_hours": 5}, "duration_days": 400},
        headers={"X-User-Id": user},
    )
    assert zero.status_code == 422
    assert huge.status_code == 422

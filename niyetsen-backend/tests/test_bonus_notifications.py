from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    Plan, PlanDay, PushTokenRecord, Task, UserProfile,
)
from app.services import bonus_service, notification_service, push_service
from app.services import intent_service
from app.storage.repository import InMemoryRepository, repo

client = TestClient(app)


def test_bonus_completion_awards_ten_points_once():
    user_id = "bonus-route-user"
    offer = client.post(
        "/bonus/offer", headers={"X-User-Id": user_id}
    )
    assert offer.status_code == 200
    body = offer.json()
    completion = {"completion_id": "client-completion-1"}
    first = client.post(
        f"/bonus/{body['id']}/complete",
        json=completion,
        headers={"X-User-Id": user_id},
    )
    second = client.post(
        f"/bonus/{body['id']}/complete",
        json=completion,
        headers={"X-User-Id": user_id},
    )
    assert first.status_code == 200
    assert first.json()["awarded"] == 10
    assert second.status_code == 409
    assert repo.get_state(user_id).points[body["category"]] == 10
    assert len([
        event for event in repo.get_point_log(user_id)
        if event.reason.startswith("motivasyon bonus görevi:")
    ]) == 1


def test_chat_yaptim_completes_active_bonus_without_model(monkeypatch):
    user_id = "bonus-chat-user"
    client.post(
        "/me/consent",
        headers={"X-User-Id": user_id},
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )
    offer = client.post(
        "/bonus/offer", headers={"X-User-Id": user_id}
    ).json()

    async def should_not_run(*args, **kwargs):
        raise AssertionError("Bonus onayı modele gitmemeli")

    monkeypatch.setattr(intent_service, "generate_json", should_not_run)
    response = client.post(
        "/chat",
        headers={"X-User-Id": user_id},
        json={
            "messages": [
                {"id": "bonus-chat-completion", "role": "user", "content": "Yaptım"}
            ]
        },
    )
    assert response.status_code == 200
    assert "+10 puan" in response.json()["reply"]
    assert repo.get_state(user_id).points[offer["category"]] == 10


def test_notification_cron_is_timezone_and_token_idempotent(monkeypatch):
    repository = InMemoryRepository()
    user_id = "push-user"
    today = date(2026, 7, 11)
    repository.save_profile(
        user_id,
        UserProfile(timezone="Europe/Istanbul", notif_hour=8),
    )
    repository.save_plan(
        user_id,
        Plan(
            id="push-plan",
            duration_days=1,
            batch_generated_until=1,
            start_date=today,
            days=[PlanDay(day=1, tasks=[Task(
                id="push-task",
                day=1,
                date=today,
                title="On dakika yürü",
                categories=["İrade"],
            )])],
        ),
    )
    repository.upsert_push_token(PushTokenRecord(
        user_id=user_id,
        token="ExpoPushToken[test-token]",
        platform="ios",
    ))
    sent: list[push_service.PushMessage] = []

    def fake_send(messages, timeout=15):
        sent.extend(messages)
        return [{"status": "ok"} for _ in messages]

    monkeypatch.setattr(push_service, "send", fake_send)
    now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)  # 15:00 Istanbul
    first = notification_service.run_due_notifications(repository, now)
    second = notification_service.run_due_notifications(repository, now)

    assert first == {
        "task_reminders_sent": 1,
        "tarot_pushes_sent": 1,
        "bonus_offers_sent": 1,
        "delivery_errors": 0,
    }
    assert second == {
        "task_reminders_sent": 0,
        "tarot_pushes_sent": 0,
        "bonus_offers_sent": 0,
        "delivery_errors": 0,
    }
    assert {message.data["url"] for message in sent} == {"/daily", "/tarot", "/bonus"}
    assert bonus_service.active_offer(repository, user_id) is not None


def test_tarot_push_is_one_minute_after_task_slot_and_idempotent(monkeypatch):
    repository = InMemoryRepository()
    user_id = "tarot-push-user"
    today = date(2026, 7, 11)
    repository.save_profile(
        user_id,
        UserProfile(timezone="Europe/Istanbul", notif_hour=8, notif_minute=0),
    )
    repository.upsert_push_token(PushTokenRecord(
        user_id=user_id,
        token="ExpoPushToken[tarot-test]",
        platform="ios",
    ))
    sent: list[push_service.PushMessage] = []

    def fake_send(messages, timeout=15):
        sent.extend(messages)
        return [{"status": "ok"} for _ in messages]

    monkeypatch.setattr(push_service, "send", fake_send)

    before_slot = datetime(2026, 7, 11, 4, 59, tzinfo=timezone.utc)  # 07:59 Istanbul
    assert notification_service.run_due_notifications(repository, before_slot) == {
        "task_reminders_sent": 0,
        "tarot_pushes_sent": 0,
        "bonus_offers_sent": 0,
        "delivery_errors": 0,
    }
    assert sent == []

    at_slot = datetime(2026, 7, 11, 5, 1, tzinfo=timezone.utc)  # 08:01 Istanbul
    first = notification_service.run_due_notifications(repository, at_slot)
    second = notification_service.run_due_notifications(repository, at_slot)

    assert first == {
        "task_reminders_sent": 0,
        "tarot_pushes_sent": 1,
        "bonus_offers_sent": 0,
        "delivery_errors": 0,
    }
    assert second == {
        "task_reminders_sent": 0,
        "tarot_pushes_sent": 0,
        "bonus_offers_sent": 0,
        "delivery_errors": 0,
    }
    assert len(sent) == 1
    assert sent[0].data["url"] == "/tarot"
    assert sent[0].title == "Bugünün kartı seni bekliyor"

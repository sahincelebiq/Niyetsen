"""main runtime/sözleşme kırıkları: thread degrade, boş yanıt, mazeret şekli."""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    CHAT_CONTENT_MAX,
    GameState,
    Plan,
    PlanDay,
    PlanEvent,
    Task,
    UserProfile,
    clip_chat_content,
)
from app.services import intent_service
from app.storage.db_coerce import visible_event_rows
from app.storage.repository import repo
from tests.conftest import grant_chat_consent

client = TestClient(app)


def test_clip_chat_content_caps_at_schema_limit() -> None:
    assert clip_chat_content("kısa") == "kısa"
    assert len(clip_chat_content("x" * (CHAT_CONTENT_MAX + 50))) == CHAT_CONTENT_MAX


def test_invalid_gender_from_db_does_not_500() -> None:
    profile = UserProfile(gender="", timezone="Europe/Istanbul")
    assert profile.gender is None
    junk = UserProfile(gender="other", timezone="Europe/Istanbul")
    assert junk.gender is None


def test_task_row_garbage_coerces_instead_of_validation_error() -> None:
    task = Task(
        id="t1",
        day=1,
        title="Su iç",
        task_type="bilinmeyen",
        categories=["yok", "İrade", "İrade"],
        status="weird",
    )
    assert task.task_type == "alışkanlık"
    assert task.status == "pending"
    assert task.categories == ["İrade"]


def test_visible_event_rows_skip_soft_deleted() -> None:
    rows = visible_event_rows([
        {"id": "live", "deleted_at": None},
        {"id": "gone", "deleted_at": "2026-09-20T00:00:00+00:00"},
        {"id": "legacy"},
    ])
    assert [row["id"] for row in rows] == ["live", "legacy"]


def test_chat_reset_survives_thread_create_failure(monkeypatch) -> None:
    user = "reset-degrade-user"
    grant_chat_consent(user, client)

    def boom(*_args, **_kwargs):
        raise RuntimeError("chat_threads yazılamadı")

    monkeypatch.setattr(repo, "create_chat_thread", boom)
    resp = client.post("/chat/reset", headers={"X-User-Id": user})
    assert resp.status_code == 200
    assert resp.json()["message"]


def test_chat_history_and_session_survive_read_failure(monkeypatch) -> None:
    user = "history-degrade-user"

    def boom(*_args, **_kwargs):
        raise RuntimeError("chat_msgs okunamadı")

    monkeypatch.setattr(repo, "get_chat_history", boom)
    history = client.get("/chat/history", headers={"X-User-Id": user})
    session = client.get("/chat/session", headers={"X-User-Id": user})
    assert history.status_code == 200
    assert history.json() == []
    assert session.status_code == 200
    assert session.json()["messages"] == []


def test_chat_threads_list_survives_read_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("chat_threads okunamadı")

    monkeypatch.setattr(repo, "list_chat_threads", boom)
    resp = client.get("/chat/threads", headers={"X-User-Id": "threads-degrade"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_chat_intent_save_failure_does_not_drop_reply(monkeypatch) -> None:
    async def fake_handle_chat(req, **_kwargs):
        from app.models.schemas import ChatResponse, CollectedIntent

        return ChatResponse(
            reply="Hangi şehirdesin?",
            ready_for_plan=False,
            collected=req.collected or CollectedIntent(),
        )

    def boom(*_args, **_kwargs):
        raise RuntimeError("intents yazılamadı")

    monkeypatch.setattr(intent_service, "handle_chat", fake_handle_chat)
    monkeypatch.setattr(repo, "save_intent", boom)
    user = "intent-degrade-user"
    grant_chat_consent(user, client)
    resp = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "İstanbul'dayım"}], "collected": {}},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    assert "şehir" in resp.json()["reply"]


def test_overlong_chat_reply_is_clipped_not_500(monkeypatch) -> None:
    huge = "A" * (CHAT_CONTENT_MAX + 200)

    async def fake_handle_chat(req, **_kwargs):
        from app.models.schemas import ChatResponse, CollectedIntent

        return ChatResponse(
            reply=huge,
            ready_for_plan=False,
            collected=req.collected or CollectedIntent(),
        )

    monkeypatch.setattr(intent_service, "handle_chat", fake_handle_chat)
    user = "long-reply-user"
    grant_chat_consent(user, client)
    resp = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "anlat"}], "collected": {}},
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    assert len(resp.json()["reply"]) == CHAT_CONTENT_MAX
    saved = client.get("/chat/history", headers={"X-User-Id": user}).json()
    assert saved
    assert len(saved[-1]["content"]) == CHAT_CONTENT_MAX


def test_greeting_survives_daily_tasks_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("tasks/daily patladı")

    monkeypatch.setattr(
        "app.services.project_service.get_daily_tasks_response", boom
    )
    user = "greet-degrade"
    grant_chat_consent(user, client)
    resp = client.get("/chat/greeting", headers={"X-User-Id": user})
    assert resp.status_code == 200
    assert resp.json()["message"]


def test_daily_tasks_survives_unexpected_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("plan satırı bozuk")

    monkeypatch.setattr(
        "app.services.project_service.get_daily_tasks_response", boom
    )
    resp = client.get("/tasks/daily", headers={"X-User-Id": "daily-degrade"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["events"] == []
    assert body["has_active_plan"] is False


def test_excuse_response_shape_matches_mobile() -> None:
    user = "excuse-shape-user"
    repo.save_plan(
        user,
        Plan(
            id="excuse-shape-plan",
            duration_days=7,
            batch_generated_until=1,
            start_date=date.today(),
            days=[
                PlanDay(
                    day=1,
                    tasks=[
                        Task(
                            id="excuse-shape-task",
                            day=1,
                            date=date.today(),
                            title="Yürüyüş",
                            categories=["İrade"],
                        )
                    ],
                )
            ],
        ),
    )
    state = GameState(user_id=user)
    state.points["İrade"] = 40
    repo.save_state(state)
    resp = client.post(
        "/task/excuse-shape-task/excuse",
        headers={"X-User-Id": user},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"]
    assert isinstance(body["events"], list)
    assert all({"category", "delta", "reason"} <= set(event) for event in body["events"])
    assert {key for event in body["events"] for key in event} <= {
        "category", "delta", "reason",
    }


def test_state_includes_last_active_day() -> None:
    user = "state-day-user"
    state = GameState(user_id=user, last_active_date=date(2026, 9, 19))
    repo.save_state(state)
    resp = client.get("/me/state", headers={"X-User-Id": user})
    assert resp.status_code == 200
    assert resp.json()["last_active_day"] == "2026-09-19"


def test_league_board_survives_read_failure(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("league_members okunamadı")

    monkeypatch.setattr(
        "app.services.league_service.get_board", boom
    )
    resp = client.get("/league", headers={"X-User-Id": "lig-degrade"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["opted_in"] is False
    assert body["members"] == []
    assert "avatar" not in body
    assert "region" not in body


def test_plan_event_unknown_category_does_not_500() -> None:
    event = PlanEvent(
        id="e1",
        user_id="u",
        plan_id="p",
        title="Su iç",
        categories=["yok", "Özsaygı"],
        start_date=date(2026, 9, 20),
        created_by="script",
        recurrence="yearly",
    )
    assert event.categories == ["Özsaygı"]
    assert event.created_by == "user"
    assert event.recurrence == "none"

"""
Niyetsen — Sohbet Geçmişi Kalıcılığı Testi (Faz 2)
Önceden sohbet mesajları sadece mobil local state'te yaşıyordu (uygulama
kapanınca/silinince kaybolur). Bu test /chat çağrısının mesajları repo'ya
yazdığını ve GET /chat/history ile geri okunabildiğini doğrular — çift kayıt
olmadan (istemci her istekte TÜM geçmişi tekrar gönderir).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import CollectedIntent
from app.services import intent_service
from app.storage.repository import repo

client = TestClient(app)

FAKE_REPLY = {
    "reply": "Hangi şehirdesin?",
    "ready_for_plan": False,
    "collected": {},
}


@pytest.fixture(autouse=True)
def _mock_gemini(monkeypatch):
    async def fake_generate_json(*args, **kwargs):
        return FAKE_REPLY

    monkeypatch.setattr(intent_service, "generate_json", fake_generate_json)


def test_chat_persists_welcome_user_and_assistant_messages():
    user_id = "chat_hist_user_1"
    messages = [
        {"role": "assistant", "content": "Merhaba 🌙"},
        {"role": "user", "content": "İstanbul'dayım"},
    ]
    resp = client.post(
        "/chat",
        json={"messages": messages, "collected": {}},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200

    hist = client.get("/chat/history", headers={"X-User-Id": user_id})
    assert hist.status_code == 200
    saved = hist.json()
    assert [m["content"] for m in saved] == [
        "Merhaba 🌙", "İstanbul'dayım", FAKE_REPLY["reply"],
    ]
    assert [m["role"] for m in saved] == ["assistant", "user", "assistant"]


def test_chat_does_not_duplicate_already_saved_messages_on_second_call():
    user_id = "chat_hist_user_2"
    first_messages = [
        {"role": "assistant", "content": "Merhaba 🌙"},
        {"role": "user", "content": "Ankara'dayım"},
    ]
    client.post(
        "/chat", json={"messages": first_messages, "collected": {}},
        headers={"X-User-Id": user_id},
    )

    second_messages = first_messages + [
        {"role": "assistant", "content": FAKE_REPLY["reply"]},
        {"role": "user", "content": "Spor ve müzik seviyorum"},
    ]
    client.post(
        "/chat", json={"messages": second_messages, "collected": {}},
        headers={"X-User-Id": user_id},
    )

    hist = client.get("/chat/history", headers={"X-User-Id": user_id})
    saved = hist.json()
    # 2 tur: her turda 1 yeni kullanıcı mesajı + 1 asistan cevabı = welcome + 4
    assert len(saved) == 5
    assert saved[-2]["content"] == "Spor ve müzik seviyorum"
    assert saved[-1]["content"] == FAKE_REPLY["reply"]


def test_chat_history_empty_for_new_user():
    resp = client.get("/chat/history", headers={"X-User-Id": "brand_new_user"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_same_client_message_id_is_idempotent():
    user_id = "chat_hist_idempotent"
    messages = [
        {"id": "welcome-fixed", "role": "assistant", "content": "Merhaba 🌙"},
        {"id": "user-fixed", "role": "user", "content": "İzmir'deyim"},
    ]
    for _ in range(2):
        resp = client.post(
            "/chat",
            json={"messages": messages, "collected": {}},
            headers={"X-User-Id": user_id},
        )
        assert resp.status_code == 200

    saved = client.get(
        "/chat/history", headers={"X-User-Id": user_id}
    ).json()
    assert [message["id"] for message in saved].count("user-fixed") == 1


def test_chat_session_restores_collected_and_ready_state():
    user_id = "chat_session_user"
    collected = CollectedIntent(
        city="İstanbul", interests=["spor"], weekly_hours=5
    )
    repo.save_intent(user_id, collected, 365, ready_for_plan=True)

    session = client.get(
        "/chat/session", headers={"X-User-Id": user_id}
    )
    assert session.status_code == 200
    assert session.json()["collected"]["city"] == "İstanbul"
    assert session.json()["ready_for_plan"] is True

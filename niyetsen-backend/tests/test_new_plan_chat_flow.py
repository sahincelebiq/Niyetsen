"""FAZ 8.9 — 'Yeni plan oluştur → sohbete bağlan' uçtan uca akışı.

Şahin'in bildirdiği canlı hata (2026-08-05): Planım'dan yeni plan oluşturunca
sohbet bağlanmıyordu. Bu test zinciri backend sözleşmesini kilitler:
/projects/new → /chat/session temiz oturum → /chat intent modunda yanıt verir.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import intent_service
from app.models.schemas import ChatResponse, CollectedIntent
from app.storage.repository import repo
from tests.conftest import grant_chat_consent

client = TestClient(app)
USER = "new-plan-chat-user"
HEADERS = {"X-User-Id": USER}


@pytest.fixture(autouse=True)
def _mock_chat(monkeypatch):
    async def fake_handle_chat(req, **kwargs):
        return ChatResponse(
            reply="Yeni niyetin için buradayım — neyi değiştirmek istiyorsun?",
            ready_for_plan=False,
            collected=req.collected or CollectedIntent(),
        )

    monkeypatch.setattr(intent_service, "handle_chat", fake_handle_chat)


def test_new_project_resets_chat_session_and_chat_responds():
    grant_chat_consent(USER, client)

    # 1) Eski oturumda mesaj varmış gibi başla
    first = client.post("/projects/new", headers=HEADERS)
    assert first.status_code == 200
    chat1 = client.post(
        "/chat", headers=HEADERS,
        json={"messages": [{"role": "user", "content": "merhaba"}], "collected": {}},
    )
    assert chat1.status_code == 200

    # 2) Yeni plan (ikinci proje → abonelik gerekir; test için pro ver)
    repo.update_subscription(USER, subscription_status="active")
    second = client.post("/projects/new", headers=HEADERS)
    assert second.status_code == 200
    new_plan = second.json()
    assert new_plan["is_active"] is True
    assert new_plan["has_content"] is False

    # 3) /chat/session TEMİZ oturum döndürmeli (eski mesajlar sızmaz)
    session = client.get("/chat/session", headers=HEADERS)
    assert session.status_code == 200
    body = session.json()
    assert body["messages"] == []          # yeni thread boş
    assert body["plan_has_content"] is False
    assert body["ready_for_plan"] is False
    assert body["active_plan_name"] == new_plan["name"]

    # 4) Sohbet YENİ oturumda cevap veriyor (intent modu)
    chat2 = client.post(
        "/chat", headers=HEADERS,
        json={"messages": [{"role": "user", "content": "spor planı istiyorum"}],
              "collected": {}},
    )
    assert chat2.status_code == 200
    assert "niyetin" in chat2.json()["reply"].casefold()

    # 5) Yeni mesaj yeni thread'e yazıldı; session'da görünür
    session2 = client.get("/chat/session", headers=HEADERS)
    contents = [m["content"] for m in session2.json()["messages"]]
    assert "spor planı istiyorum" in contents
    assert "merhaba" not in contents       # eski plan sohbeti karışmaz

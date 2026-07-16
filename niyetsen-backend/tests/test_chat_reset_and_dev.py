"""FAZ 7.5: yeni sohbet başlat (chat reset) + geliştirici hesabı ayrımı."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import dev_accounts
from app.main import app
from app.models.schemas import ChatMessage
from app.services import subscription_service
from tests.conftest import grant_chat_consent

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_dev_registry():
    dev_accounts.reset()
    yield
    dev_accounts.reset()


# ---------------- Yeni sohbet başlat ----------------
def test_chat_reset_clears_history_but_keeps_plan(isolated_in_memory_repo):
    repo = isolated_in_memory_repo
    user = "reset_user"
    grant_chat_consent(user, client)
    repo.append_chat_messages(user, [
        ChatMessage(id="m1", role="user", content="selam"),
        ChatMessage(id="m2", role="assistant", content="hoş geldin"),
    ])
    assert len(client.get("/chat/history", headers={"X-User-Id": user}).json()) == 2

    resp = client.post("/chat/reset", headers={"X-User-Id": user})
    assert resp.status_code == 200
    assert resp.json()["message"]  # taze karşılama döner

    assert client.get("/chat/history", headers={"X-User-Id": user}).json() == []
    # Plan/niyet yapısı yerinde: yeni mesaj eklenebilir (aktif plan korunur)
    repo.append_chat_message(user, ChatMessage(id="m3", role="user", content="devam"))
    assert len(client.get("/chat/history", headers={"X-User-Id": user}).json()) == 1


def test_chat_reset_on_empty_history_is_safe():
    user = "reset_empty"
    grant_chat_consent(user, client)
    resp = client.post("/chat/reset", headers={"X-User-Id": user})
    assert resp.status_code == 200


# ---------------- Geliştirici hesabı ----------------
def test_dev_email_gets_premium_without_purchase(isolated_in_memory_repo):
    dev_accounts.register_if_dev("dev-user-1", "kutluadalarr7@gmail.com")
    info = subscription_service.get_subscription(isolated_in_memory_repo, "dev-user-1")
    assert info.has_premium_access is True
    assert info.show_paywall is False
    assert info.status == "active"


def test_normal_user_flow_unchanged(isolated_in_memory_repo):
    dev_accounts.register_if_dev("normal-user", "baskabiri@example.com")
    assert dev_accounts.is_dev("normal-user") is False
    info = subscription_service.get_subscription(isolated_in_memory_repo, "normal-user")
    # Standart akış: dev kısa devresi YOK (free/trial mantığı neyse o).
    assert info.status in {"free", "trial", "expired", "active", "cancelled"}


def test_dev_email_matching_is_case_insensitive():
    dev_accounts.register_if_dev("dev-user-2", "KutluAdalarr7@Gmail.com")
    assert dev_accounts.is_dev("dev-user-2") is True

"""FAZ 7.6: Sohbet oturumları — yeni sohbet eskiyi SİLMEZ (Claude tarzı)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ChatMessage
from tests.conftest import grant_chat_consent

client = TestClient(app)


def _seed(repo, user: str, texts: list[str]) -> None:
    repo.append_chat_messages(user, [
        ChatMessage(id=f"m-{i}", role="user" if i % 2 == 0 else "assistant", content=t)
        for i, t in enumerate(texts)
    ])


def test_new_chat_preserves_old_thread(isolated_in_memory_repo):
    user = "thread_user"
    grant_chat_consent(user, client)
    _seed(isolated_in_memory_repo, user, ["spor planı istiyorum", "harika, başlayalım"])

    # Yeni sohbet: eski oturum SİLİNMEZ.
    assert client.post("/chat/reset", headers={"X-User-Id": user}).status_code == 200
    assert client.get("/chat/history", headers={"X-User-Id": user}).json() == []

    threads = client.get("/chat/threads", headers={"X-User-Id": user}).json()
    assert len(threads) == 2
    titles = [t["title"] for t in threads]
    assert "spor planı istiyorum" in titles  # başlık ilk kullanıcı mesajından


def test_switch_back_to_old_thread_restores_history(isolated_in_memory_repo):
    user = "thread_switcher"
    grant_chat_consent(user, client)
    _seed(isolated_in_memory_repo, user, ["kitap okuma hedefi", "güzel hedef"])
    client.post("/chat/reset", headers={"X-User-Id": user})
    _seed(isolated_in_memory_repo, user, ["yeni konu: sabah rutini"])

    threads = client.get("/chat/threads", headers={"X-User-Id": user}).json()
    old = next(t for t in threads if t["title"] == "kitap okuma hedefi")

    resp = client.post(
        f"/chat/threads/{old['id']}/activate", headers={"X-User-Id": user}
    )
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert contents == ["kitap okuma hedefi", "güzel hedef"]


def test_activate_unknown_thread_404():
    user = "thread_404"
    grant_chat_consent(user, client)
    resp = client.post(
        "/chat/threads/olmayan-id/activate", headers={"X-User-Id": user}
    )
    assert resp.status_code == 404


def test_active_thread_flag_in_list(isolated_in_memory_repo):
    user = "thread_active_flag"
    grant_chat_consent(user, client)
    _seed(isolated_in_memory_repo, user, ["ilk sohbet"])
    client.post("/chat/reset", headers={"X-User-Id": user})

    threads = client.get("/chat/threads", headers={"X-User-Id": user}).json()
    active = [t for t in threads if t["is_active"]]
    assert len(active) == 1
    assert active[0]["title"] == ""  # yeni oturum henüz başlıksız

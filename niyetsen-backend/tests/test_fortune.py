"""FAZ 7 (V2): Fal modülü — tarot, kahve/el, burç, hak sayaçları."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import fortune_service
from app.storage.repository import repo
from tests.conftest import grant_chat_consent

client = TestClient(app)

JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 200


def grant_pro(user_id: str) -> None:
    """Fal uçları PRO (trial/active) — test kullanıcısını abone yap."""
    repo.update_subscription(user_id, subscription_status="active")


def grant_all_consents(user_id: str) -> None:
    grant_chat_consent(user_id, client)
    grant_pro(user_id)
    response = client.post(
        "/me/consent",
        headers={"X-User-Id": user_id},
        json={"proof_photo_processing": {"accepted": True}},
    )
    assert response.status_code == 200


@pytest.fixture(autouse=True)
def _mock_gemini(monkeypatch):
    async def fake_generate_json(*args, **kwargs):
        return {"interpretation": "Kartlar bugünkü niyetine ayna tutuyor."}

    async def fake_generate_json_with_images(*args, **kwargs):
        return {
            "is_valid_photo": True,
            "symbols": ["kuş", "yol"],
            "interpretation": "Telvede yeni bir yol görünüyor; küçük adımla başla.",
        }

    monkeypatch.setattr(fortune_service, "generate_json", fake_generate_json)
    monkeypatch.setattr(
        fortune_service, "generate_json_with_images", fake_generate_json_with_images
    )


# ---------------- Tarot ----------------
def test_tarot_draw_returns_three_cards_and_logs():
    user = "tarot_user"
    grant_chat_consent(user, client)
    grant_pro(user)
    resp = client.post(
        "/fortune/tarot", headers={"X-User-Id": user}, json={"question": "işim?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cards"]) == 3
    assert body["already_drawn_today"] is False
    assert "eğlence" in body["disclaimer"].lower()
    positions = [c["position"] for c in body["cards"]]
    assert positions == ["geçmiş", "şimdi", "niyetin yönü"]


def test_tarot_second_draw_same_day_returns_cached():
    user = "tarot_cached"
    grant_chat_consent(user, client)
    grant_pro(user)
    first = client.post("/fortune/tarot", headers={"X-User-Id": user}, json={})
    second = client.post("/fortune/tarot", headers={"X-User-Id": user}, json={})
    assert second.status_code == 200
    assert second.json()["already_drawn_today"] is True
    assert second.json()["cards"] == first.json()["cards"]


def test_tarot_requires_consent():
    resp = client.post(
        "/fortune/tarot", headers={"X-User-Id": "no_consent"}, json={}
    )
    assert resp.status_code == 403


def test_tarot_crisis_signal_stops_reading():
    user = "crisis_user"
    grant_chat_consent(user, client)
    grant_pro(user)
    resp = client.post(
        "/fortune/tarot",
        headers={"X-User-Id": user},
        json={"question": "yaşamak istemiyorum artık"},
    )
    assert resp.status_code == 400
    assert "destek" in resp.json()["detail"]


# ---------------- Kahve / El ----------------
def _upload(user: str, kind: str):
    return client.post(
        f"/fortune/photo/{kind}",
        headers={"X-User-Id": user},
        files={"photo": ("fal.jpg", JPEG_BYTES, "image/jpeg")},
    )


def test_coffee_fortune_flow_and_daily_limit():
    user = "kahve_user"
    grant_all_consents(user)
    rights = client.get("/fortune/rights", headers={"X-User-Id": user}).json()
    limit = rights["rights"]["kahve"]["limit"]  # free=1, deneme/premium=3

    first = _upload(user, "kahve")
    assert first.status_code == 200
    assert first.json()["symbols"] == ["kuş", "yol"]
    assert first.json()["remaining_today"] == limit - 1

    for _ in range(limit - 1):
        assert _upload(user, "kahve").status_code == 200
    assert _upload(user, "kahve").status_code == 429  # günlük hak doldu


def test_palm_fortune_separate_counter():
    user = "el_user"
    grant_all_consents(user)
    assert _upload(user, "kahve").status_code == 200
    assert _upload(user, "el").status_code == 200  # ayrı sayaç


def test_invalid_photo_does_not_burn_right(monkeypatch):
    async def rejecting(*args, **kwargs):
        return {"is_valid_photo": False}

    monkeypatch.setattr(fortune_service, "generate_json_with_images", rejecting)
    user = "bad_photo_user"
    grant_all_consents(user)
    resp = _upload(user, "kahve")
    assert resp.status_code == 400

    async def accepting(*args, **kwargs):
        return {"is_valid_photo": True, "symbols": [], "interpretation": "yorum"}

    monkeypatch.setattr(fortune_service, "generate_json_with_images", accepting)
    assert _upload(user, "kahve").status_code == 200  # hak yanmadı


def test_photo_fortune_requires_photo_consent():
    user = "only_chat_consent"
    grant_chat_consent(user, client)
    resp = _upload(user, "kahve")
    assert resp.status_code == 403


def test_unknown_kind_404():
    user = "kind_404"
    grant_all_consents(user)
    assert _upload(user, "yildizname").status_code == 404


# ---------------- Burç ----------------
def test_horoscope_requires_birth_date():
    user = "no_birth"
    grant_chat_consent(user, client)
    grant_pro(user)
    resp = client.get("/fortune/horoscope", headers={"X-User-Id": user})
    assert resp.status_code == 400


def test_horoscope_with_profile_and_daily_cache():
    user = "burc_user"
    grant_chat_consent(user, client)
    grant_pro(user)
    update = client.put(
        "/me/profile",
        headers={"X-User-Id": user},
        json={"name": "Şahin", "birth_date": "1995-04-05"},
    )
    assert update.status_code == 200

    first = client.get("/fortune/horoscope", headers={"X-User-Id": user})
    assert first.status_code == 200
    assert first.json()["sign"] == "Koç"

    second = client.get("/fortune/horoscope", headers={"X-User-Id": user})
    assert second.status_code == 200
    assert second.json()["interpretation"] == first.json()["interpretation"]


def test_weekly_horoscope_separate_cache():
    user = "burc_hafta"
    grant_chat_consent(user, client)
    grant_pro(user)
    client.put(
        "/me/profile",
        headers={"X-User-Id": user},
        json={"name": "Şahin", "birth_date": "1995-04-05"},
    )
    daily = client.get("/fortune/horoscope?period=daily", headers={"X-User-Id": user})
    weekly = client.get("/fortune/horoscope?period=weekly", headers={"X-User-Id": user})
    assert daily.status_code == 200
    assert weekly.status_code == 200
    assert weekly.json()["sign"] == "Koç"

    invalid = client.get("/fortune/horoscope?period=aylik", headers={"X-User-Id": user})
    assert invalid.status_code == 400


# ---------------- Geçmiş ----------------
def test_fortune_history_lists_recent_first():
    user = "history_user"
    grant_all_consents(user)
    client.post("/fortune/tarot", headers={"X-User-Id": user}, json={})
    _upload(user, "kahve")

    resp = client.get("/fortune/history", headers={"X-User-Id": user})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["type"] == "kahve"  # en yeni önce
    assert body[1]["type"] == "tarot"
    assert body[1]["result"]["cards"]


def test_fortune_history_requires_consent():
    resp = client.get("/fortune/history", headers={"X-User-Id": "hist_no_consent"})
    assert resp.status_code == 403


# ---------------- faz8.13 — fal ücretsiz + çoklu foto + mistik sohbet ------
def test_tarot_free_user_no_paywall():
    """faz8.13: fal ÜCRETSİZDİR — PRO kapısı yok, hak sayaçları sunucuda."""
    user = "tarot_free"
    grant_chat_consent(user, client)  # abonelik YOK
    resp = client.post("/fortune/tarot", headers={"X-User-Id": user}, json={})
    assert resp.status_code == 200
    assert len(resp.json()["cards"]) == 3


def test_photo_fortune_free_user_no_paywall():
    user = "photo_free"
    grant_chat_consent(user, client)
    client.post(
        "/me/consent", headers={"X-User-Id": user},
        json={"proof_photo_processing": {"accepted": True}},
    )
    assert _upload(user, "kahve").status_code == 200


def test_coffee_multi_photo_capped_at_three():
    """faz8.13/2d: kahvede en fazla 3 kare — fazlası sessizce kırpılır."""
    user = "kahve_multi"
    grant_all_consents(user)
    files = [
        ("photos", (f"fal{i}.jpg", JPEG_BYTES, "image/jpeg")) for i in range(4)
    ]
    resp = client.post(
        f"/fortune/photo/kahve", headers={"X-User-Id": user}, files=files
    )
    assert resp.status_code == 200
    assert resp.json()["kind"] == "kahve"


def test_mystic_chat_replies_with_disclaimer():
    """faz8.13/2b: mistik rehber sohbeti — yanıt + disclaimer, kriz değil."""
    user = "mystic_chat_user"
    grant_chat_consent(user, client)
    resp = client.post(
        "/fortune/chat", headers={"X-User-Id": user},
        json={"messages": [{"role": "user", "content": "bugün nasıl bir gün olacak?"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]
    assert body["crisis"] is False
    assert "eğlence" in body["disclaimer"].lower()


def test_mystic_chat_crisis_stops_reading():
    user = "mystic_crisis"
    grant_chat_consent(user, client)
    resp = client.post(
        "/fortune/chat", headers={"X-User-Id": user},
        json={"messages": [{"role": "user", "content": "yaşamak istemiyorum artık"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["crisis"] is True
    assert "destek" in body["reply"]


def test_mystic_chat_requires_message():
    user = "mystic_empty"
    grant_chat_consent(user, client)
    resp = client.post(
        "/fortune/chat", headers={"X-User-Id": user}, json={"messages": []}
    )
    assert resp.status_code == 400


# ---------------- Haklar ----------------
def test_rights_endpoint_free_user():
    user = "rights_user"
    grant_chat_consent(user, client)
    resp = client.get("/fortune/rights", headers={"X-User-Id": user})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rights"]["tarot"]["limit"] == 1
    assert body["rights"]["kahve"]["limit"] in (1, 3)
    assert body["rights"]["burc"]["limit"] == -1

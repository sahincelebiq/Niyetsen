from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.core.prompt_builder import build_memory_block
from app.models.schemas import GameState
from app.services.profile_service import zodiac_for

client = TestClient(app)


def test_zodiac_boundaries():
    assert zodiac_for(date(1990, 3, 20)) == "Balık"
    assert zodiac_for(date(1990, 3, 21)) == "Koç"
    assert zodiac_for(date(1990, 12, 22)) == "Oğlak"


def test_memory_block_includes_onboarding_identity():
    memory = build_memory_block(
        GameState(user_id="memory-user"),
        name="Şahin",
        birth_date="2001-07-01",
        zodiac="Yengeç",
    )
    assert "İsim: Şahin" in memory
    assert "Doğum tarihi: 2001-07-01" in memory
    assert "Burç: Yengeç" in memory


def test_profile_requires_kvkk_consent():
    response = client.put(
        "/me/profile",
        headers={"X-User-Id": "profile_no_consent"},
        json={
            "name": "Şahin",
            "birth_date": "1995-04-10",
            "notif_hour": 8,
            "timezone": "Europe/Istanbul",
            "kvkk_consent": False,
        },
    )
    assert response.status_code == 422


def test_profile_onboarding_round_trip():
    user_id = "profile_round_trip"
    response = client.put(
        "/me/profile",
        headers={"X-User-Id": user_id},
        json={
            "name": "Şahin",
            "birth_date": "1995-04-10",
            "notif_hour": 9,
            "timezone": "Europe/Istanbul",
            "kvkk_consent": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["zodiac_sign"] == "Koç"
    assert response.json()["onboarding_complete"] is True

    fetched = client.get("/me/profile", headers={"X-User-Id": user_id})
    assert fetched.json()["name"] == "Şahin"
    assert fetched.json()["notif_hour"] == 9


def test_profile_persists_irade_mode():
    user_id = "profile_irade_mode"
    response = client.put(
        "/me/profile",
        headers={"X-User-Id": user_id},
        json={
            "name": "Şahin",
            "birth_date": "1995-04-10",
            "notif_hour": 9,
            "timezone": "Europe/Istanbul",
            "kvkk_consent": True,
            "irade_modu_active": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["irade_modu_active"] is True
    assert client.get(
        "/me/profile", headers={"X-User-Id": user_id}
    ).json()["irade_modu_active"] is True


def test_future_birth_date_rejected():
    response = client.put(
        "/me/profile",
        headers={"X-User-Id": "profile_future"},
        json={
            "name": "Test",
            "birth_date": (date.today() + timedelta(days=1)).isoformat(),
            "notif_hour": 8,
            "timezone": "Europe/Istanbul",
            "kvkk_consent": True,
        },
    )
    assert response.status_code == 422


def test_delete_account_clears_in_memory_profile():
    user_id = "profile_delete"
    client.put(
        "/me/profile",
        headers={"X-User-Id": user_id},
        json={
            "name": "Silinecek",
            "birth_date": "1995-04-10",
            "notif_hour": 8,
            "timezone": "Europe/Istanbul",
            "kvkk_consent": True,
        },
    )
    deleted = client.delete("/me", headers={"X-User-Id": user_id})
    assert deleted.status_code == 204
    fetched = client.get("/me/profile", headers={"X-User-Id": user_id})
    assert fetched.json()["onboarding_complete"] is False

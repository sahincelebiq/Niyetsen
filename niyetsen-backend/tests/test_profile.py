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
        today_status="1 done, 1 pending",
        recent_tasks="Yürüyüş (done)",
        mood_notes="Bugün enerjik hissediyorum",
    )
    assert "İsim: Şahin" in memory
    assert "Doğum tarihi: 2001-07-01" in memory
    assert "Burç: Yengeç" in memory
    assert "Bugün durumu: 1 done, 1 pending" in memory
    assert "Son görevler: Yürüyüş (done)" in memory
    assert "Son ruh hali notları: Bugün enerjik hissediyorum" in memory
    assert "Zincir:" in memory
    assert "plan günü DEĞİL" in memory


def test_memory_block_separates_plan_day_from_streak():
    memory = build_memory_block(
        GameState(user_id="memory-plan-day", streak_len=40, best_streak=40),
        plan_day=7,
        duration_days=365,
        philosophy_paths=["Sisu Yolu"],
    )
    assert "Plan günü: 7/365" in memory
    assert "zincir değil" in memory
    assert "Zincir: 40 gün" in memory
    assert "plan günü DEĞİL" in memory
    assert "Aktif felsefe yolu: Sisu Yolu" in memory
    assert memory.index("Plan günü") < memory.index("Zincir:")


def test_profile_can_be_saved_before_consent_without_implied_rejection():
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
    assert response.status_code == 200
    assert response.json()["onboarding_complete"] is False


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

"""Karşılama metni testleri."""
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ConsentChoice, ConsentUpdate, ProfileUpdate, UserProfile
from app.services import consent_service, profile_service
from app.services.greeting_service import build_chat_greeting
from app.storage.repository import repo

client = TestClient(app)


def test_morning_greeting_with_name():
    text = build_chat_greeting(name="Ayşe", timezone_name="Europe/Istanbul")
    assert text.startswith("Günaydın Ayşe!") or text.startswith("İyi günler Ayşe!") or text.startswith("İyi akşamlar Ayşe!")


def test_greeting_without_name():
    text = build_chat_greeting(name=None, timezone_name="Europe/Istanbul")
    assert "Günaydın" in text or "İyi günler" in text or "İyi akşamlar" in text
    assert "Ben Niyetsen" in text


def test_invalid_timezone_falls_back():
    text = build_chat_greeting(name="Ali", timezone_name="Invalid/Zone")
    assert "Ali" in text


def test_chat_greeting_endpoint():
    user_id = "greeting_user"
    consent_service.update(repo, user_id, ConsentUpdate(
        privacy_policy=ConsentChoice(accepted=True),
        kvkk_explicit_consent=ConsentChoice(accepted=True),
        ai_chat_processing=ConsentChoice(accepted=True),
    ))
    profile_service_update = ProfileUpdate(
        name="Deniz",
        birth_date="1990-01-01",
        timezone="Europe/Istanbul",
        notif_hour=9,
    )
    repo.save_profile(
        user_id,
        profile_service.build_profile(profile_service_update, UserProfile()),
    )

    resp = client.get("/chat/greeting", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    body = resp.json()
    assert "Deniz" in body["message"]
    assert "Niyetsen" in body["message"]

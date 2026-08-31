"""Karşılama metni testleri."""
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ConsentChoice, ConsentUpdate, Plan, PlanDay, ProfileUpdate, Task, UserProfile
from app.services import consent_service, profile_service
from app.services.greeting_service import build_chat_greeting
from app.storage.repository import repo

client = TestClient(app)


def test_greeting_follows_english_locale():
    text = build_chat_greeting(
        name="Ayse",
        timezone_name="Europe/Istanbul",
        locale="en-US",
    )
    assert "Niyetsen" in text
    assert "Ben Niyetsen" not in text
    assert "Good morning" in text or "Good afternoon" in text or "Good evening" in text


def test_greeting_normalizes_en_leak():
    text = build_chat_greeting(name=None, timezone_name="Europe/Istanbul", locale="en")
    assert "I’m Niyetsen" in text or "I'm Niyetsen" in text
    assert "Ben Niyetsen" not in text


def test_morning_greeting_with_name():
    text = build_chat_greeting(name="Ayşe", timezone_name="Europe/Istanbul")
    assert text.startswith("Günaydın Ayşe!") or text.startswith("İyi günler Ayşe!") or text.startswith("İyi akşamlar Ayşe!")


def test_greeting_without_name():
    text = build_chat_greeting(name=None, timezone_name="Europe/Istanbul")
    assert "Günaydın" in text or "İyi günler" in text or "İyi akşamlar" in text
    assert "Ben Niyetsen" in text


def test_greeting_with_streak_and_pending_tasks():
    text = build_chat_greeting(
        name="Ayşe",
        timezone_name="Europe/Istanbul",
        streak_len=5,
        pending_tasks_today=2,
        active_plan_name="Sabah Rutini",
        has_plan=True,
    )
    assert "5 günlük zincirin" in text
    assert "2 görev" in text
    assert "Sabah Rutini" in text


def test_greeting_completed_today_celebrates():
    text = build_chat_greeting(
        name="Ayşe",
        timezone_name="Europe/Istanbul",
        pending_tasks_today=0,
        completed_tasks_today=2,
        has_plan=True,
    )
    assert "tamamladın" in text


def test_greeting_needs_extension_points_to_today_tab():
    text = build_chat_greeting(
        name="Ayşe",
        timezone_name="Europe/Istanbul",
        has_plan=True,
        needs_extension=True,
    )
    assert "Bugün sekmesine" in text


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


def test_chat_greeting_endpoint_with_plan_context():
    user_id = "greeting_plan_user"
    today = date.today()
    state = repo.get_state(user_id)
    state.streak_len = 3
    repo.save_state(state)
    repo.save_plan(
        user_id,
        Plan(
            id="plan_greet",
            duration_days=30,
            batch_generated_until=1,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    theme="Başlangıç",
                    tasks=[
                        Task(
                            id="task_greet",
                            day=1,
                            date=today,
                            title="Yürüyüş",
                            categories=["İrade"],
                            status="pending",
                        )
                    ],
                )
            ],
            name="Planım",
            slot_no=1,
            is_active=True,
        ),
    )
    resp = client.get("/chat/greeting", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    message = resp.json()["message"]
    assert "3 günlük zincirin" in message
    assert "1 görev" in message


def test_chat_greeting_endpoint_follows_en_locale_header():
    user_id = "greeting_en_header"
    consent_service.update(repo, user_id, ConsentUpdate(
        privacy_policy=ConsentChoice(accepted=True),
        kvkk_explicit_consent=ConsentChoice(accepted=True),
        ai_chat_processing=ConsentChoice(accepted=True),
    ))
    repo.save_profile(
        user_id,
        profile_service.build_profile(
            ProfileUpdate(
                name="Deniz",
                birth_date="1990-01-01",
                timezone="Europe/Istanbul",
                notif_hour=9,
            ),
            UserProfile(),
        ),
    )
    resp = client.get(
        "/chat/greeting",
        headers={"X-User-Id": user_id, "X-App-Locale": "en"},
    )
    assert resp.status_code == 200
    message = resp.json()["message"]
    assert "Ben Niyetsen" not in message
    assert "Good morning" in message or "Good afternoon" in message or "Good evening" in message
    assert "I’m Niyetsen" in message or "I'm Niyetsen" in message


def test_chat_reset_greeting_follows_de_locale_header():
    user_id = "greeting_reset_de"
    consent_service.update(repo, user_id, ConsentUpdate(
        privacy_policy=ConsentChoice(accepted=True),
        kvkk_explicit_consent=ConsentChoice(accepted=True),
        ai_chat_processing=ConsentChoice(accepted=True),
    ))
    resp = client.post(
        "/chat/reset",
        headers={"X-User-Id": user_id, "X-App-Locale": "de"},
    )
    assert resp.status_code == 200
    message = resp.json()["message"]
    assert "Ben Niyetsen" not in message
    assert "Guten Morgen" in message or "Guten Tag" in message or "Guten Abend" in message
    assert "Ich bin Niyetsen" in message

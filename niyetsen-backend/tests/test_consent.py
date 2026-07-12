from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)


def _headers(user_id: str) -> dict[str, str]:
    return {"X-User-Id": user_id}


def test_consent_defaults_are_granular_versioned_and_marketing_false():
    body = client.get("/me/consent", headers=_headers("consent-defaults")).json()
    assert body["data_controller"] == "Şahin Çelebi"
    assert body["contact_email"] == "ai@niyetsen.com"
    assert body["needs_reconsent"] is True
    assert body["privacy_policy"]["version"] == settings.PRIVACY_POLICY_VERSION
    assert body["privacy_policy"]["accepted"] is False
    assert body["ai_chat_processing"]["accepted"] is False
    assert body["proof_photo_processing"]["accepted"] is False
    assert body["marketing_communications"]["accepted"] is False


def test_consent_post_updates_only_supplied_current_version():
    user_id = "consent-granular"
    response = client.post(
        "/me/consent",
        headers=_headers(user_id),
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["privacy_policy"]["accepted"] is True
    assert body["kvkk_explicit_consent"]["accepted"] is True
    assert body["ai_chat_processing"]["accepted"] is True
    assert body["needs_reconsent"] is False
    assert body["proof_photo_processing"]["accepted"] is False
    assert body["marketing_communications"]["accepted"] is False


def test_chat_gate_requires_ai_and_base_legal_consents():
    response = client.post(
        "/chat",
        headers=_headers("chat-no-consent"),
        json={"messages": [{"role": "user", "content": "Merhaba"}]},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "consent_required"


def test_proof_gate_requires_photo_and_base_legal_consents():
    response = client.post(
        "/task/not-visible-before-consent/proof",
        headers=_headers("proof-no-consent"),
        files={
            "photo": (
                "proof.png",
                b"\x89PNG\r\n\x1a\n" + b"\0" * 200,
                "image/png",
            )
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "consent_required"


def test_legacy_profile_checkbox_migrates_only_privacy_and_kvkk():
    user_id = "legacy-consent"
    profile = client.put(
        "/me/profile",
        headers=_headers(user_id),
        json={
            "name": "Şahin",
            "birth_date": "1995-04-10",
            "timezone": "Europe/Istanbul",
            "notif_hour": 8,
            "kvkk_consent": True,
        },
    )
    assert profile.status_code == 200
    body = client.get("/me/consent", headers=_headers(user_id)).json()
    assert body["privacy_policy"]["accepted"] is True
    assert body["kvkk_explicit_consent"]["accepted"] is True
    assert body["ai_chat_processing"]["accepted"] is False
    assert body["proof_photo_processing"]["accepted"] is False
    assert body["marketing_communications"]["accepted"] is False


def test_explicit_false_revokes_one_purpose_without_touching_profile():
    user_id = "consent-revoke"
    client.post(
        "/me/consent",
        headers=_headers(user_id),
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )
    body = client.post(
        "/me/consent",
        headers=_headers(user_id),
        json={"ai_chat_processing": {"accepted": False}},
    ).json()
    assert body["privacy_policy"]["accepted"] is True
    assert body["ai_chat_processing"]["accepted"] is False
    assert client.get("/me/profile", headers=_headers(user_id)).status_code == 200

"""Paywall erişim kilidi HTTP testleri."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services import subscription_service
from app.storage.repository import repo

client = TestClient(app)
USER = "paywall-user"


def _auth_headers() -> dict[str, str]:
    return {"X-User-Id": USER}


def _grant_consents() -> None:
    client.post(
        "/me/consent",
        headers=_auth_headers(),
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )


def test_expired_trial_blocks_chat() -> None:
    _grant_consents()
    repo.update_subscription(
        USER,
        subscription_status="trial",
        trial_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    res = client.post(
        "/chat",
        headers=_auth_headers(),
        json={
            "messages": [{"role": "user", "content": "Merhaba"}],
            "collected": {},
        },
    )
    assert res.status_code == 402
    assert res.json()["detail"]["code"] == "paywall_required"


def test_subscription_endpoint_reports_trial() -> None:
    user_id = "paywall-trial-user"
    client.post(
        "/me/consent",
        headers={"X-User-Id": user_id},
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )
    subscription_service.start_trial_if_needed(repo, user_id)
    res = client.get("/me/subscription", headers={"X-User-Id": user_id})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "trial"
    assert body["has_premium_access"] is True

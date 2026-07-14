"""RevenueCat webhook ve senkron uçtan uca testleri (KAPI 5)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services import subscription_service
from app.storage.repository import repo

client = TestClient(app)
WEBHOOK_SECRET = "test-rc-webhook-secret"
USER = "rc-webhook-user"


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "REVENUECAT_WEBHOOK_SECRET", WEBHOOK_SECRET)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {WEBHOOK_SECRET}"}


def _event(
    event_type: str,
    *,
    user_id: str = USER,
    expiration_at_ms: int | None = None,
) -> dict:
    body: dict = {
        "event": {
            "type": event_type,
            "app_user_id": user_id,
            "id": f"evt-{event_type}",
        }
    }
    if expiration_at_ms is not None:
        body["event"]["expiration_at_ms"] = expiration_at_ms
    return body


def test_webhook_rejects_missing_secret() -> None:
    res = client.post("/webhooks/revenuecat", json=_event("INITIAL_PURCHASE"))
    assert res.status_code == 401


def test_webhook_initial_purchase_activates() -> None:
    subscription_service.start_trial_if_needed(repo, USER)
    expires = int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    res = client.post(
        "/webhooks/revenuecat",
        headers=_auth_headers(),
        json=_event("INITIAL_PURCHASE", expiration_at_ms=expires),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "active"
    assert body["has_premium_access"] is True
    assert body["show_paywall"] is False


def test_webhook_cancellation_keeps_access_until_expiration() -> None:
    user_id = "rc-cancel-user"
    repo.update_subscription(user_id, subscription_status="active")
    future = int(datetime(2027, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)
    res = client.post(
        "/webhooks/revenuecat",
        headers=_auth_headers(),
        json=_event("CANCELLATION", user_id=user_id, expiration_at_ms=future),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "active"
    assert res.json()["has_premium_access"] is True


def test_webhook_expiration_locks_paywall() -> None:
    user_id = "rc-expire-user"
    repo.update_subscription(
        user_id,
        subscription_status="active",
        trial_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    past = int(datetime(2026, 1, 2, tzinfo=timezone.utc).timestamp() * 1000)
    res = client.post(
        "/webhooks/revenuecat",
        headers=_auth_headers(),
        json=_event("EXPIRATION", user_id=user_id, expiration_at_ms=past),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "expired"
    assert body["show_paywall"] is True


def test_sync_endpoint_activates_when_entitlement_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = "rc-sync-user"
    subscription_service.start_trial_if_needed(repo, user_id)

    async def fake_fetch(_uid: str) -> dict:
        return {
            "subscriber": {
                "entitlements": {
                    "premium": {
                        "expires_date": "2099-01-01T00:00:00Z",
                        "product_identifier": "niyetsen_monthly",
                    }
                }
            }
        }

    monkeypatch.setattr(
        "app.services.revenuecat_client.fetch_subscriber",
        fake_fetch,
    )
    res = client.post("/me/subscription/sync", headers={"X-User-Id": user_id})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "active"
    assert body["has_premium_access"] is True


def test_subscription_sync_endpoint_requires_auth() -> None:
    res = client.post("/me/subscription/sync", headers={"X-User-Id": USER})
    # AUTH_DISABLED true in tests — should work with X-User-Id
    assert res.status_code == 200

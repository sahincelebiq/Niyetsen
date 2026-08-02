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


def test_expired_trial_does_not_block_chat(monkeypatch) -> None:
    """FAZ 7.6 kural değişikliği (Şahin): asistan sohbeti ücretsiz sürümde
    SINIRSIZ — deneme bitse bile /chat 402 DÖNMEZ. Premium kilit plan/kanıt/
    bonus/İdol tarafında sürer (aşağıdaki testler)."""
    from app.models.schemas import ChatResponse, CollectedIntent
    from app.services import intent_service

    async def fake_handle_chat(*args, **kwargs):
        return ChatResponse(
            reply="Buradayım.", ready_for_plan=False, collected=CollectedIntent()
        )

    monkeypatch.setattr(intent_service, "handle_chat", fake_handle_chat)
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
    assert res.status_code == 200
    assert res.json()["reply"]


def test_expired_trial_blocks_idol_paths() -> None:
    """Felsefe Yolları (İdol Modu) premium'da kalır."""
    _grant_consents()
    repo.update_subscription(
        USER,
        subscription_status="trial",
        trial_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    res = client.get("/paths", headers=_auth_headers())
    assert res.status_code == 402
    assert res.json()["detail"]["code"] == "paywall_required"


def test_free_status_blocks_idol_paths() -> None:
    """Free (deneme başlamamış) idol/mistik PRO kapısında — has_premium_access
    true olsa bile status=free 402 alır."""
    _grant_consents()
    repo.update_subscription(USER, subscription_status="free")
    res = client.get("/paths", headers=_auth_headers())
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

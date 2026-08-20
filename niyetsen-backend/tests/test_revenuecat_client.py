"""RevenueCat REST istemcisi — satın alma sonrası tek yedek yolun testleri.

Bu dosyadan önce fetch_subscriber'ın HTTP yolu HİÇ test edilmiyordu (%62 kapsam,
55-72 satırları kapsam dışı). Oysa webhook gecikirse/düşerse kullanıcının
erişimini açan tek mekanizma burası — sessizce bozulursa "ödedim ama
açılmadı" şikâyeti olarak geri döner.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.config import settings
from app.services import revenuecat_client


@pytest.fixture(autouse=True)
def _api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "REVENUECAT_API_KEY", "sk_test_key")
    monkeypatch.setattr(settings, "REVENUECAT_ENTITLEMENT_ID", "premium")


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler) -> dict:
    """httpx.AsyncClient'ı MockTransport ile değiştir; isteği yakala."""
    seen: dict = {}
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        def wrapped(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            return handler(request)

        kwargs["transport"] = httpx.MockTransport(wrapped)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return seen


# ---------------- fetch_subscriber ----------------
@pytest.mark.anyio
async def test_fetch_subscriber_sends_bearer_and_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _patch_transport(
        monkeypatch,
        lambda req: httpx.Response(200, json={"subscriber": {"entitlements": {}}}),
    )
    await revenuecat_client.fetch_subscriber("user-abc")
    assert seen["url"].endswith("/subscribers/user-abc")
    assert seen["auth"] == "Bearer sk_test_key"


@pytest.mark.anyio
async def test_fetch_subscriber_missing_api_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CANLI DURUM: REVENUECAT_API_KEY boşken senkron yedeği tamamen ölüdür."""
    monkeypatch.setattr(settings, "REVENUECAT_API_KEY", "")
    with pytest.raises(revenuecat_client.RevenueCatUnavailable) as exc:
        await revenuecat_client.fetch_subscriber("user-abc")
    assert "REVENUECAT_API_KEY" in str(exc.value)


@pytest.mark.anyio
async def test_fetch_subscriber_404_is_new_user_not_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RC'de kaydı olmayan kullanıcı hata değildir — boş entitlement döner."""
    _patch_transport(monkeypatch, lambda req: httpx.Response(404, json={}))
    payload = await revenuecat_client.fetch_subscriber("yeni-kullanici")
    assert payload["subscriber"]["entitlements"] == {}


@pytest.mark.anyio
async def test_fetch_subscriber_server_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_transport(
        monkeypatch, lambda req: httpx.Response(500, text="internal error")
    )
    with pytest.raises(revenuecat_client.RevenueCatUnavailable):
        await revenuecat_client.fetch_subscriber("user-abc")


@pytest.mark.anyio
async def test_fetch_subscriber_network_failure_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlantı yok", request=request)

    _patch_transport(monkeypatch, boom)
    with pytest.raises(revenuecat_client.RevenueCatUnavailable):
        await revenuecat_client.fetch_subscriber("user-abc")


@pytest.mark.anyio
async def test_fetch_subscriber_401_raises_not_silently_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Yanlış API anahtarı 'abonelik yok' gibi görünmemeli — yükseltilmeli."""
    _patch_transport(
        monkeypatch, lambda req: httpx.Response(401, text="invalid api key")
    )
    with pytest.raises(revenuecat_client.RevenueCatUnavailable):
        await revenuecat_client.fetch_subscriber("user-abc")


# ---------------- entitlement_is_active ----------------
def _payload(entitlement: dict | None, key: str = "premium") -> dict:
    return {"subscriber": {"entitlements": {key: entitlement} if entitlement else {}}}


def test_entitlement_active_when_expiry_in_future() -> None:
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    active, expires = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": future})
    )
    assert active is True
    assert expires is not None


def test_entitlement_inactive_when_expired() -> None:
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    active, expires = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": past})
    )
    assert active is False
    assert expires is not None


def test_entitlement_active_when_no_expiry_lifetime() -> None:
    """Ömür boyu satın almada expires_date null gelir — aktif sayılmalı."""
    active, expires = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": None})
    )
    assert active is True
    assert expires is None


def test_entitlement_missing_returns_inactive() -> None:
    active, expires = revenuecat_client.entitlement_is_active(_payload(None))
    assert active is False
    assert expires is None


def test_entitlement_wrong_id_returns_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dashboard'daki entitlement adı yanlışsa sessizce 'abonelik yok' olur —
    bu testin kırılması yapılandırma hatasını erken yakalar."""
    monkeypatch.setattr(settings, "REVENUECAT_ENTITLEMENT_ID", "premium")
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    active, _ = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": future}, key="pro")  # yanlış anahtar
    )
    assert active is False


def test_entitlement_z_suffix_timestamp_parses() -> None:
    """RC 'Z' ekli ISO döner; fromisoformat bunu doğrudan yiyemez."""
    active, expires = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": "2099-01-01T00:00:00Z"})
    )
    assert active is True
    assert expires is not None and expires.tzinfo is not None


def test_entitlement_malformed_date_is_treated_as_active_not_crash() -> None:
    """Bozuk tarih 500 fırlatmamalı; parse edilemeyen tarih None sayılır."""
    active, expires = revenuecat_client.entitlement_is_active(
        _payload({"expires_date": "not-a-date"})
    )
    assert expires is None
    assert active is True

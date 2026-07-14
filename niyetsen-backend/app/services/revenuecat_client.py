"""RevenueCat REST API — webhook gecikmesinde abonelik senkronu (KAPI 5)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("niyetsen.revenuecat")
RC_BASE = "https://api.revenuecat.com/v1"


class RevenueCatUnavailable(Exception):
    pass


def _entitlement_id() -> str:
    return (settings.REVENUECAT_ENTITLEMENT_ID or "premium").strip()


def _parse_expires(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        log.warning("RevenueCat expires_date parse edilemedi: %s", value)
        return None


def entitlement_is_active(subscriber_payload: dict[str, Any]) -> tuple[bool, datetime | None]:
    """RC subscriber yanıtında entitlement aktif mi?"""
    entitlements = (
        subscriber_payload.get("subscriber", {}).get("entitlements", {}) or {}
    )
    entitlement = entitlements.get(_entitlement_id())
    if not entitlement:
        return False, None
    expires = _parse_expires(entitlement.get("expires_date"))
    if expires is None:
        return True, None
    now = datetime.now(timezone.utc)
    return expires > now, expires


async def fetch_subscriber(app_user_id: str) -> dict[str, Any]:
    api_key = settings.REVENUECAT_API_KEY.strip()
    if not api_key:
        raise RevenueCatUnavailable("REVENUECAT_API_KEY yapılandırılmamış.")

    url = f"{RC_BASE}/subscribers/{app_user_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise RevenueCatUnavailable(str(exc)) from exc

    if response.status_code == 404:
        return {"subscriber": {"entitlements": {}}}
    if response.status_code >= 400:
        raise RevenueCatUnavailable(
            f"RevenueCat HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json()

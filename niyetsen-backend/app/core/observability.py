"""Opsiyonel hata izleme — SENTRY_DSN yoksa no-op.

KVKK: istek gövdesi, çerez, query ve Authorization gitmez. E-posta ve JWT
before_send'de maskelenir. Yerel değişkenler (sohbet, prompt) eklenmez.
Kullanıcı kimliği bu katmanda bağlanmaz.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings

log = logging.getLogger("niyetsen.observability")
_initialized = False

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# Padding'li imza (`=`) da JWT'dir; yoksa token'ın sonu sızıyordu.
_JWT = re.compile(
    r"eyJ[A-Za-z0-9_-]{8,}={0,2}"
    r"\.[A-Za-z0-9_-]{8,}={0,2}"
    r"\.[A-Za-z0-9_-]{8,}={0,2}"
)
_KEEP_HEADERS = frozenset({"content-type", "user-agent", "x-request-id"})
# İşlem izleri (transaction) query'yi request.query_string dışında
# span attribute ve breadcrumb url alanına da yazar.
_DROP_KEYS = frozenset({
    "query_string", "http.query", "url.query", "cookies", "cookie",
})
_URL_KEYS = frozenset({"url", "url.full"})


def _scrub_text(value: str) -> str:
    value = _JWT.sub("[token]", value)
    return _EMAIL.sub("[e-posta]", value)


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, dict):
        return {_scrub_text(str(key)): _scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub(item) for item in value)
    return value


def _filter_headers(headers: Any) -> Any:
    if isinstance(headers, dict):
        return {
            key: value
            for key, value in headers.items()
            if str(key).lower() in _KEEP_HEADERS
        }
    if isinstance(headers, list):
        kept = []
        for item in headers:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and str(item[0]).lower() in _KEEP_HEADERS
            ):
                kept.append([item[0], item[1]])
        return kept
    return {}


def _strip_transport(value: Any, *, in_request: bool = False) -> Any:
    """Gövde, çerez ve query'yi event'in her yerinden çıkarır."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_s = str(key)
            if key_s in _DROP_KEYS:
                continue
            if in_request and key_s == "data":
                continue
            if key_s == "headers":
                item = _filter_headers(item)
            if key_s in _URL_KEYS and isinstance(item, str):
                item = item.split("?", 1)[0]
            cleaned[key_s] = _strip_transport(
                item, in_request=(key_s == "request")
            )
        return cleaned
    if isinstance(value, list):
        return [_strip_transport(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_transport(item) for item in value)
    return value


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    stripped = _strip_transport(event)
    scrubbed = _scrub(stripped)
    return scrubbed if isinstance(scrubbed, dict) else None


def init_observability() -> None:
    global _initialized
    if _initialized or not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Log satırı breadcrumb olur; olay yalnız capture_exception ile gider
        # (logger.exception + ERROR eşiği aynı hatayı iki kez açardı).
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            release=f"niyetsen-api@{settings.API_VERSION}",
            send_default_pii=False,
            include_local_variables=False,
            max_request_body_size="never",
            before_send=_before_send,
            before_send_transaction=_before_send,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=None),
            ],
            traces_sample_rate=0.1 if settings.ENV == "prod" else 0.0,
        )
        _initialized = True
        log.info("sentry=on env=%s", settings.ENV)
    except ImportError:
        log.warning("sentry-sdk yüklü değil; SENTRY_DSN yok sayılıyor.")


def capture_exception(exc: BaseException, **extra: Any) -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                if value is None or value == "":
                    continue
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        log.exception("Yakalanmamış hata", exc_info=exc)

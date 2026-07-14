"""Opsiyonel hata izleme — SENTRY_DSN yoksa no-op."""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings

log = logging.getLogger("niyetsen.observability")
_initialized = False


def init_observability() -> None:
    global _initialized
    if _initialized or not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1 if settings.ENV == "prod" else 0.0,
        )
        _initialized = True
    except ImportError:
        log.warning("sentry-sdk yüklü değil; SENTRY_DSN yok sayılıyor.")


def capture_exception(exc: BaseException, **extra: Any) -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    except ImportError:
        log.exception("Yakalanmamış hata", exc_info=exc)

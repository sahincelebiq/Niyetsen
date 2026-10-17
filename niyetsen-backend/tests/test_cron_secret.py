"""HTTP cron secret gate — defense-only regression.

`test_cron_direct.py` doğrudan script yolunu dener; bu dosya X-Cron-Secret
doğrulamasının yanlış/eksik/boş sırda sessizce geçmediğini kilitler.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
CRON_SECRET = "test-cron-secret"
CRON_PATHS = ("/cron/close-day", "/cron/notifications")


@pytest.fixture
def cron_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "CRON_SECRET", CRON_SECRET)
    return CRON_SECRET


@pytest.fixture
def noop_cron_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.task_lifecycle_service.close_due_users",
        lambda *args, **kwargs: {"results": []},
    )
    monkeypatch.setattr(
        "app.api.routes.notification_service.run_due_notifications",
        lambda *args, **kwargs: {"sent": 0},
    )


@pytest.mark.parametrize("path", CRON_PATHS)
def test_cron_rejects_missing_secret(cron_secret: str, path: str) -> None:
    res = client.post(path)
    assert res.status_code == 401


@pytest.mark.parametrize("path", CRON_PATHS)
def test_cron_rejects_wrong_secret(cron_secret: str, path: str) -> None:
    res = client.post(path, headers={"X-Cron-Secret": "wrong-cron-secret"})
    assert res.status_code == 401


@pytest.mark.parametrize("path", CRON_PATHS)
def test_cron_returns_503_when_secret_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(settings, "CRON_SECRET", "")
    res = client.post(path, headers={"X-Cron-Secret": CRON_SECRET})
    assert res.status_code == 503


@pytest.mark.parametrize("path", CRON_PATHS)
def test_cron_accepts_matching_secret(
    cron_secret: str,
    noop_cron_handlers: None,
    path: str,
) -> None:
    res = client.post(path, headers={"X-Cron-Secret": cron_secret})
    assert res.status_code == 200

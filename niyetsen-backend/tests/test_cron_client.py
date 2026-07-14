"""Tests for Railway cron HTTP fallback (local dev only)."""
from __future__ import annotations

import httpx
import pytest

import scripts.run_scheduled_jobs as cron_jobs


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = '{"ok":true}') -> None:
        self.status_code = status_code
        self.text = text

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400


def test_http_mode_soft_fails_notifications_timeout(monkeypatch):
    monkeypatch.setenv("CRON_EXECUTION_MODE", "http")
    monkeypatch.setenv("API_BASE_URL", "https://api.test")
    monkeypatch.setenv("CRON_SECRET", "secret")
    monkeypatch.setenv("CRON_MAX_RETRIES", "1")

    def fake_post(self, url, headers=None):
        if url.endswith("/cron/close-day"):
            return _FakeResponse()
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    hard, soft = cron_jobs.run_jobs_http()
    assert hard == []
    assert any("notifications" in item for item in soft)


def test_execution_mode_defaults_to_direct(monkeypatch):
    monkeypatch.delenv("CRON_EXECUTION_MODE", raising=False)
    assert cron_jobs._execution_mode() == "direct"


def test_require_direct_env_lists_missing(monkeypatch):
    monkeypatch.delenv("USE_SUPABASE_DB", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="USE_SUPABASE_DB"):
        cron_jobs._require_direct_env()

"""Tests for Railway cron HTTP client resilience."""
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


def test_post_with_retry_succeeds_after_timeout(monkeypatch):
    attempts = {"count": 0}

    def fake_post(self, url, headers=None):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise httpx.ReadTimeout("timed out")
        return _FakeResponse()

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    monkeypatch.setattr(cron_jobs, "MAX_RETRIES", 3)
    monkeypatch.setattr(cron_jobs, "RETRY_BACKOFF_SEC", (0, 0, 0))

    with httpx.Client(timeout=cron_jobs._client_timeout()) as client:
        response = cron_jobs._post_with_retry(client, "https://api.test/cron/close-day", {})

    assert response.status_code == 200
    assert attempts["count"] == 2


def test_post_with_retry_raises_after_exhausted(monkeypatch):
    def fake_post(self, url, headers=None):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    monkeypatch.setattr(cron_jobs, "MAX_RETRIES", 2)
    monkeypatch.setattr(cron_jobs, "RETRY_BACKOFF_SEC", (0, 0))

    with httpx.Client(timeout=cron_jobs._client_timeout()) as client:
        with pytest.raises(httpx.ReadTimeout):
            cron_jobs._post_with_retry(client, "https://api.test/cron/close-day", {})

"""Paylaşılan test yardımcıları ve izolasyon."""
from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.storage.repository import InMemoryRepository


@pytest.fixture(autouse=True)
def isolated_in_memory_repo(monkeypatch: pytest.MonkeyPatch) -> InMemoryRepository:
    """Her testte bellek-içi repo; yerel .env USE_SUPABASE_DB=true olsa bile."""
    test_repo = InMemoryRepository()
    monkeypatch.setattr("app.storage.repository.repo", test_repo)
    monkeypatch.setattr("app.api.routes.repo", test_repo)
    for module in sys.modules.values():
        name = getattr(module, "__name__", "")
        if name.startswith("tests.") and hasattr(module, "repo"):
            monkeypatch.setattr(module, "repo", test_repo, raising=False)
    monkeypatch.setattr(settings, "USE_SUPABASE_DB", False)
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)
    return test_repo


def grant_chat_consent(user_id: str, client: TestClient) -> None:
    response = client.post(
        "/me/consent",
        headers={"X-User-Id": user_id},
        json={
            "privacy_policy": {"accepted": True},
            "kvkk_explicit_consent": {"accepted": True},
            "ai_chat_processing": {"accepted": True},
        },
    )
    assert response.status_code == 200

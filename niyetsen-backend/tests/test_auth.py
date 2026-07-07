"""
Niyetsen — JWT Kimlik Doğrulama Testleri (MASTER_PLAN §1.6)
AUTH_DISABLED=false olduğunda /health hariç her endpoint geçerli Supabase JWT ister.
"""
from __future__ import annotations

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

TEST_SECRET = "test-secret"


@pytest.fixture(autouse=True)
def _enable_jwt(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", TEST_SECRET)
    yield


def _token(sub: str = "user-abc") -> str:
    return jwt.encode({"sub": sub, "aud": "authenticated"}, TEST_SECRET, algorithm="HS256")


def test_health_does_not_require_auth():
    assert client.get("/health").status_code == 200


def test_missing_token_returns_401():
    assert client.get("/me/state").status_code == 401


def test_invalid_token_returns_401():
    resp = client.get("/me/state", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_wrong_secret_returns_401():
    bad_token = jwt.encode({"sub": "user-abc", "aud": "authenticated"}, "wrong-secret", algorithm="HS256")
    resp = client.get("/me/state", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401


def test_x_user_id_header_alone_is_not_enough_when_auth_enabled():
    resp = client.get("/me/state", headers={"X-User-Id": "sahin"})
    assert resp.status_code == 401


def test_valid_token_authenticates():
    resp = client.get("/me/state", headers={"Authorization": f"Bearer {_token('user-abc')}"})
    assert resp.status_code == 200

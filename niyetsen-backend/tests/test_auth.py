"""
Niyetsen — JWT Kimlik Doğrulama Testleri (MASTER_PLAN §1.6)
AUTH_DISABLED=false olduğunda /health hariç her endpoint geçerli Supabase JWT
(JWKS/RS256) ister. Gerçek Supabase JWKS endpoint'i yerine sahte bir RSA
anahtar çifti ve sahte PyJWKClient kullanılır — ağ çağrısı yok.
"""
from __future__ import annotations

from dataclasses import dataclass

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from starlette.requests import Request

import app.api.routes as routes
from app.config import settings
from app.core.rate_limit import _identity
from app.main import app

client = TestClient(app)

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class _FakeSigningKey:
    key: object


class _FakeJWKClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(key=_PRIVATE_KEY.public_key())


@pytest.fixture(autouse=True)
def _enable_jwt(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    monkeypatch.setattr(routes, "_get_jwks_client", lambda: _FakeJWKClient())
    yield


def _token(sub: str = "user-abc") -> str:
    return jwt.encode({"sub": sub, "aud": "authenticated"}, _PRIVATE_KEY, algorithm="RS256")


def test_health_does_not_require_auth():
    assert client.get("/health").status_code == 200


def test_missing_token_returns_401():
    assert client.get("/me/state").status_code == 401


def test_invalid_token_returns_401():
    resp = client.get("/me/state", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_wrong_key_returns_401():
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad_token = jwt.encode({"sub": "user-abc", "aud": "authenticated"}, other_key, algorithm="RS256")
    resp = client.get("/me/state", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401


def test_x_user_id_header_alone_is_not_enough_when_auth_enabled():
    resp = client.get("/me/state", headers={"X-User-Id": "sahin"})
    assert resp.status_code == 401


def test_valid_token_authenticates():
    resp = client.get("/me/state", headers={"Authorization": f"Bearer {_token('user-abc')}"})
    assert resp.status_code == 200


def test_rate_limit_identity_survives_jwt_refresh_for_same_user():
    first = _token("stable-user")
    second = jwt.encode(
        {"sub": "stable-user", "aud": "authenticated", "nonce": "refreshed"},
        _PRIVATE_KEY,
        algorithm="RS256",
    )

    def request_for(token: str) -> Request:
        return Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [
                (b"authorization", f"Bearer {token}".encode()),
            ],
        })

    assert _identity(request_for(first)) == "user:stable-user"
    assert _identity(request_for(second)) == "user:stable-user"

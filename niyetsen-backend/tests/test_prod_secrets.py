"""ENV=prod sır doğrulaması. Değerler loga yazılmaz; yalnız varlık kontrolü."""
import pytest

from app.config import settings, validate_prod_secrets

_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"


def _prod(monkeypatch, **overrides: str) -> None:
    monkeypatch.setattr(settings, "ENV", "prod")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyTestKeyValue123456")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", _JWT)
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "unsplash-access-key")
    monkeypatch.setattr(settings, "REVENUECAT_API_KEY", "sk_test_revenuecat_key")
    for name, value in overrides.items():
        monkeypatch.setattr(settings, name, value)


def test_prod_secrets_accept_real_looking_values(monkeypatch):
    _prod(monkeypatch)
    validate_prod_secrets()


def test_prod_rejects_blank_gemini(monkeypatch):
    _prod(monkeypatch, GEMINI_API_KEY="")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        validate_prod_secrets()


def test_prod_rejects_placeholder_and_bad_url(monkeypatch):
    _prod(monkeypatch, GEMINI_API_KEY="your-api-key-placeholder")
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        validate_prod_secrets()
    _prod(monkeypatch, SUPABASE_URL="http://insecure.example")
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        validate_prod_secrets()


def test_dev_skips_validation(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    validate_prod_secrets()

"""M-04 / M-05: prod'da OpenAPI ve /health bilgi sızıntısı kilitleri."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes
from app.config import settings
from app.main import _openapi_docs_kwargs, app

client = TestClient(app)


def test_dev_health_keeps_diagnostics() -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["env"] == settings.ENV
    assert "model_chat" in body
    assert "model_plan" in body


def test_prod_health_is_minimal_status_only(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENV", "prod")
    body = client.get("/health").json()
    assert body == {"status": "ok"}
    # Doğrudan handler da aynı sözleşmeyi tutar (TestClient dışı).
    assert routes.health() == {"status": "ok"}


def test_dev_openapi_surface_stays_available() -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_prod_openapi_surface_returns_404() -> None:
    kwargs = _openapi_docs_kwargs("prod")
    assert kwargs == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    locked = TestClient(FastAPI(**kwargs))
    assert locked.get("/docs").status_code == 404
    assert locked.get("/redoc").status_code == 404
    assert locked.get("/openapi.json").status_code == 404

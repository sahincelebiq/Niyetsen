"""FAZ 8.9 — İdol/Felsefe Yolu detay endpoint'i."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import persona_service
from app.storage.repository import repo

client = TestClient(app)
USER = "path-detail-user"
HEADERS = {"X-User-Id": USER}


def _grant_pro() -> None:
    repo.update_subscription(USER, subscription_status="active")


def test_path_detail_requires_premium():
    repo.update_subscription("path-free", subscription_status="free")
    slug = persona_service.list_personas()[0].slug
    response = client.get(f"/paths/{slug}", headers={"X-User-Id": "path-free"})
    assert response.status_code == 402


def test_path_detail_returns_safe_sections():
    _grant_pro()
    persona = persona_service.list_personas()[0]
    response = client.get(f"/paths/{persona.slug}", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == persona.slug
    assert "ilham" in body["source_note"].casefold()  # yasal not zorunlu
    keys = {section["key"] for section in body["sections"]}
    assert "public_quotes" not in keys  # alıntılar bilerek dışarıda
    assert keys  # en az bir dossier bölümü dolu


def test_path_detail_unknown_slug_404():
    _grant_pro()
    response = client.get("/paths/olmayan-yol", headers=HEADERS)
    assert response.status_code == 404

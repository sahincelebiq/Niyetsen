"""Dalga 4: İdol Modu / Felsefe Yolları — RAG + plan bağlamı."""
from __future__ import annotations

import pytest

from app.config import settings
from app.models.schemas import CollectedIntent
from app.services import plan_service, rag_service


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    monkeypatch.setattr(settings, "RAG_EMBEDDINGS_ENABLED", False)
    rag_service.reset_cache()
    yield
    rag_service.reset_cache()


def test_idol_source_loads_five_paths():
    chunks = rag_service.retrieve("felsefe yolu", sources=["idoller"], k=20)
    text = "\n".join(chunks)
    for path in ("Greenlights", "Kaizen", "Stoacı", "Ustalık", "Şafak"):
        assert path in text, f"{path} Yolu bilgi tabanında bulunamadı"


def test_idol_trigger_pulls_idol_source_in_chat():
    chunks = rag_service.retrieve_for_chat(
        "Matthew McConaughey gibi olmak istiyorum, bir filmden çok etkilendim"
    )
    assert any("[idoller" in chunk for chunk in chunks)


def test_person_name_maps_to_greenlights_content():
    chunks = rag_service.retrieve("mcconaughey greenlights engel", sources=["idoller"], k=3)
    assert chunks
    assert "Greenlights" in chunks[0]


def test_plan_injects_path_context_when_interest_is_path():
    collected = CollectedIntent(
        city="İstanbul", interests=["Kaizen Yolu"], weekly_hours=5
    )
    block = plan_service._philosophy_path_block(collected)
    assert "FELSEFE YOLU BAĞLAMI" in block
    assert "Kaizen" in block
    assert "kişi adı KULLANMA" in block


def test_plan_no_path_context_for_normal_interests():
    collected = CollectedIntent(
        city="İstanbul", interests=["spor", "kitap"], weekly_hours=5
    )
    assert plan_service._philosophy_path_block(collected) == ""


def test_paths_endpoint_lists_five_paths():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import path_service

    path_service.reset_cache()
    client = TestClient(app)
    resp = client.get("/paths", headers={"X-User-Id": "paths_user"})
    assert resp.status_code == 200
    body = resp.json()
    names = [p["name"] for p in body]
    assert len(body) >= 5
    assert "Greenlights Yolu" in names
    for p in body:
        assert p["tagline"]
        assert p["philosophy"]

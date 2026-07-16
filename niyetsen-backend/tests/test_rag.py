"""FAZ 7 (V2): RAG servisi — bilgi tabanı chunk'ları ve keyword fallback."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services import rag_service


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    """Testler ağsız: embedding kapalı → keyword fallback deterministik."""
    monkeypatch.setattr(settings, "RAG_EMBEDDINGS_ENABLED", False)
    rag_service.reset_cache()
    yield
    rag_service.reset_cache()


def test_knowledge_base_loads_chunks():
    chunks = rag_service.retrieve("zincir motivasyon", k=10)
    assert chunks, "knowledge/ boş olmamalı"
    assert all(chunk.startswith("[") for chunk in chunks)  # etiketli format


def test_source_filter_limits_results():
    chunks = rag_service.retrieve("Koç burcu enerji", sources=["burclar"], k=5)
    assert chunks
    assert all("[burclar" in chunk for chunk in chunks)


def test_chat_retrieval_uses_personal_growth_sources():
    chunks = rag_service.retrieve_for_chat("bugün motivasyonum yok, zinciri kıracağım")
    assert chunks
    assert all(
        any(src in chunk for src in ("[felsefe", "[motivasyon", "[atomik", "[senaryolar"))
        for chunk in chunks
    )


def test_chat_retrieval_adds_mystic_source_on_trigger():
    chunks = rag_service.retrieve_for_chat("burcum Koç, bugün nasılım?")
    assert any("[burclar" in chunk for chunk in chunks)


def test_rag_disabled_returns_empty(monkeypatch):
    monkeypatch.setattr(settings, "RAG_ENABLED", False)
    assert rag_service.retrieve("herhangi bir şey") == []


def test_empty_query_returns_empty():
    assert rag_service.retrieve("   ") == []

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
        any(src in chunk for src in (
            "[felsefe", "[motivasyon", "[atomik", "[senaryolar", "[kategoriler",
        ))
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


def test_chat_retrieval_adds_coffee_source_on_trigger():
    chunks = rag_service.retrieve_for_chat("kahve falı baktıracağım, telvede ne var")
    assert any("[kahve_fali" in chunk for chunk in chunks)


def test_chat_retrieval_adds_palm_source_on_trigger():
    chunks = rag_service.retrieve_for_chat("el falı bak, avuç içi çizgilerim")
    assert any("[el_fali" in chunk for chunk in chunks)


def test_chat_retrieval_does_not_leak_mystic_on_plain_motivation():
    chunks = rag_service.retrieve_for_chat("bugün motivasyonum yok, zinciri kıracağım")
    joined = "\n".join(chunks)
    assert "[kahve_fali" not in joined
    assert "[el_fali" not in joined
    assert "[tarot" not in joined
    assert "[burclar" not in joined


def test_category_knowledge_reachable_on_trigger():
    """Release QA T4: 6 kategori bilgi tabanı sohbete girer."""
    chunks = rag_service.retrieve_for_chat("disiplinimi nasıl güçlendiririm?")
    assert any("[kategoriler" in chunk for chunk in chunks)


def test_zodiac_synthesis_reachable_on_trigger():
    """Release QA T5: burç × kategori sentezi burç konuşulunca gelir."""
    chunks = rag_service.retrieve_for_chat("burcuma göre nasıl gelişirim? Koç burcuyum")
    assert any("[burc_gelisim" in chunk for chunk in chunks)


def test_profile_hint_personalizes_retrieval():
    """Release QA T3: aynı mesaj, farklı profil ipucu → farklı bilgi seti."""
    message = "bugün ne yapayım, biraz yönsüz hissediyorum"
    plain = rag_service.retrieve_for_chat(message)
    hinted = rag_service.retrieve_for_chat(message, profile_hint="Özsaygı İstikrar")
    assert hinted  # ipuçlu sorgu boş dönmez
    assert hinted != plain or any("Özsaygı" in c for c in hinted)


def test_keyword_prefers_heading_match():
    chunks = rag_service.retrieve(
        "zincir kırıldı her şey mahvoldu",
        sources=["senaryolar"],
        k=2,
        use_embeddings=False,
    )
    assert chunks
    assert "Zincir kırıldı" in chunks[0] or "zincir" in chunks[0].casefold()

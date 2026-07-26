"""Dalga 4.3: Persona dossier katmanı — yükleme, eşleme, hukuki çerçeve."""
from __future__ import annotations

from app.services import persona_service


def setup_function() -> None:
    persona_service.reset_cache()


def test_persona_files_load():
    personas = persona_service.list_personas(force_reload=True)
    assert personas, "knowledge/personas/ altında en az bir dossier olmalı"
    assert any(p.slug == "greenlights-yolu" for p in personas)


def test_path_name_is_philosophy_not_person():
    for persona in persona_service.list_personas(force_reload=True):
        assert "yol" in persona.path_name.casefold(), persona.path_name
        if persona.inspired_by:
            # Kişi adı paket adında geçemez (kişilik hakları + Apple 5.2.1)
            assert persona.inspired_by.casefold() not in persona.path_name.casefold()


def test_source_note_always_has_disclaimer():
    for persona in persona_service.list_personas(force_reload=True):
        if persona.inspired_by:
            assert "bağlantılı değildir" in persona.source_note


def test_match_persona_from_person_name():
    persona = persona_service.match_persona(
        "Sahara filmini izledim, McConaughey gibi olmak istiyorum"
    )
    assert persona is not None
    assert persona.path_name == "Greenlights Yolu"


def test_chunks_are_rag_sized():
    persona = persona_service.get_persona("greenlights-yolu")
    assert persona is not None
    chunks = persona_service.build_chunks(persona)
    assert chunks
    for chunk in chunks:
        assert 0 < len(chunk["text"].split()) <= 160
        assert chunk["text"].startswith("[")  # etiketli blok


def test_context_block_carries_legal_note_and_rule():
    persona = persona_service.get_persona("Greenlights Yolu")
    assert persona is not None
    context = persona_service.context_for(persona)
    assert "bağlantılı değildir" in context
    assert "kişi adı KULLANMA" in context


def test_paths_endpoint_includes_dossier_and_markdown_paths():
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import path_service

    path_service.reset_cache()
    client = TestClient(app)
    resp = client.get("/paths", headers={"X-User-Id": "persona_paths_user"})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Greenlights Yolu" in names       # dossier kaynağı
    assert "Kaizen Yolu" in names            # markdown kaynağı (birleşme)

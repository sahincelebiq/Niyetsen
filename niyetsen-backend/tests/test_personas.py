"""Dalga 4.3: Persona dossier katmanı — yükleme, eşleme, hukuki çerçeve."""
from __future__ import annotations

from app.services import persona_service


def setup_function() -> None:
    persona_service.reset_cache()


def test_persona_files_load():
    personas = persona_service.list_personas(force_reload=True)
    assert personas, "knowledge/personas/ altında en az bir dossier olmalı"
    slugs = {p.slug for p in personas}
    assert "greenlights-yolu" in slugs
    assert "amor-fati-yolu" in slugs
    assert "sisu-yolu" in slugs
    assert "wu-wei-yolu" in slugs


def test_list_personas_keeps_file_only_slugs_when_db_is_subset(monkeypatch):
    """Prod'da eski idol_personas satırı yeni JSON yolları gizlemez."""
    files = persona_service._load_from_files()
    subset = [p for p in files if p.slug == "greenlights-yolu"]
    assert subset
    monkeypatch.setattr(persona_service, "_load_from_db", lambda: subset)
    personas = persona_service.list_personas(force_reload=True)
    slugs = {p.slug for p in personas}
    assert "greenlights-yolu" in slugs
    assert "amor-fati-yolu" in slugs
    assert "sisu-yolu" in slugs
    assert "wu-wei-yolu" in slugs


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
    from app.storage.repository import repo

    path_service.reset_cache()
    repo.update_subscription("persona_paths_user", subscription_status="active")
    client = TestClient(app)
    resp = client.get("/paths", headers={"X-User-Id": "persona_paths_user"})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Greenlights Yolu" in names       # dossier kaynağı
    assert "Kaizen Yolu" in names            # markdown kaynağı (birleşme)
    assert "Amor Fati Yolu" in names
    assert "Sisu Yolu" in names
    assert "Wu Wei Yolu" in names


def test_seed_today_lessons_adds_idempotent_tasks(isolated_in_memory_repo):
    from datetime import date

    from app.models.schemas import Plan, PlanDay, Task

    today = date(2026, 8, 30)
    isolated_in_memory_repo.save_plan(
        "path-seed-user",
        Plan(
            id="path-seed-plan",
            duration_days=30,
            batch_generated_until=7,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    theme="Başlangıç",
                    tasks=[
                        Task(
                            id="existing",
                            day=1,
                            date=today,
                            title="Su iç",
                            categories=["İstikrar"],
                        )
                    ],
                )
            ],
        ),
    )
    persona = persona_service.get_persona("sisu-yolu")
    assert persona is not None
    added = persona_service.seed_today_lessons(
        isolated_in_memory_repo, "path-seed-user", persona, today=today
    )
    assert added
    titles = {t.title for t in isolated_in_memory_repo.list_tasks_for_date("path-seed-user", today)}
    assert "Su iç" in titles
    assert any("dakika" in title.casefold() or "adım" in title.casefold() for title in titles)
    again = persona_service.seed_today_lessons(
        isolated_in_memory_repo, "path-seed-user", persona, today=today
    )
    assert again == []


def test_apply_path_chat_seeds_today_and_sets_ready_without_plan(
    isolated_in_memory_repo, monkeypatch,
):
    from datetime import date

    from fastapi.testclient import TestClient

    from app.main import app
    from app.models.schemas import ChatResponse, CollectedIntent, Plan, PlanDay, Task
    from app.services import intent_service
    from tests.conftest import grant_chat_consent

    today = date.today()

    async def fake_handle_chat(req, **kwargs):
        return ChatResponse(
            reply="Yolunu duydum.",
            ready_for_plan=False,
            collected=req.collected or CollectedIntent(),
        )

    monkeypatch.setattr(intent_service, "handle_chat", fake_handle_chat)
    client = TestClient(app)
    grant_chat_consent("path-apply-user", client)

    empty = client.post(
        "/chat",
        headers={"X-User-Id": "path-apply-user"},
        json={
            "messages": [{
                "role": "user",
                "content": "Sisu Yolu ile ilerlemek istiyorum — bitince bir adım daha. Bu yolu niyetime işler misin?",
            }],
            "collected": {},
        },
    )
    assert empty.status_code == 200
    body = empty.json()
    assert body["ready_for_plan"] is True
    assert "Sisu Yolu" in body["collected"]["interests"]
    assert "niyetine işlendi" in body["reply"]

    isolated_in_memory_repo.save_plan(
        "path-apply-user",
        Plan(
            id="path-apply-plan",
            duration_days=30,
            batch_generated_until=1,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    theme="Başlangıç",
                    tasks=[
                        Task(
                            id="keep",
                            day=1,
                            date=today,
                            title="Nefes al",
                            categories=["İrade"],
                        )
                    ],
                )
            ],
        ),
    )
    with_plan = client.post(
        "/chat",
        headers={"X-User-Id": "path-apply-user"},
        json={
            "messages": [{
                "role": "user",
                "content": "Amor Fati Yolu ile ilerlemek istiyorum — olanı yakıt saymak. Bu yolu niyetime işler misin?",
            }],
            "collected": {"interests": ["Sisu Yolu"], "city": "İstanbul", "weekly_hours": 5},
        },
    )
    assert with_plan.status_code == 200
    reply = with_plan.json()
    assert "Amor Fati Yolu" in reply["collected"]["interests"]
    assert "bugünün planına işlendi" in reply["reply"]
    today_titles = [
        t.title
        for t in isolated_in_memory_repo.list_tasks_for_date("path-apply-user", today)
    ]
    assert "Nefes al" in today_titles
    assert len(today_titles) >= 2

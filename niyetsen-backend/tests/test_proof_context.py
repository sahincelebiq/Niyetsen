"""FAZ 8.6 — kanıt prompt'una kişisel GÖREV BAĞLAMI dolar."""
from __future__ import annotations

import asyncio

from app.core import prompts
from app.services import proof_service


def test_evaluate_proof_prompt_includes_personal_context(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_generate_json_with_image(*, prompt, image_bytes, mime_type):
        captured["prompt"] = prompt
        return {"matches": True, "confidence": 80, "reason": "Meyve tabağı görünüyor."}

    monkeypatch.setattr(
        proof_service, "generate_json_with_image", fake_generate_json_with_image
    )

    jpeg = b"\xff\xd8\xff" + b"\x00" * 200
    result = asyncio.run(
        proof_service.evaluate_proof(
            task_title="Akşam meyve tabağı hazırla",
            image_bytes=jpeg,
            mime_type="image/jpeg",
            attempt_no=1,
            tiny_version="Bir elma ye",
            categories=["Özsaygı"],
            task_type="alışkanlık",
            plan_name="Sporcu yazı",
            day_theme="Beslenme disiplini",
            task_context="Aynı gün diğer görevler: 20 dk yürüyüş",
        )
    )

    assert result.approved is True
    prompt = captured["prompt"]
    assert "GÖREV BAĞLAMI" in prompt
    assert "Sporcu yazı" in prompt
    assert "Beslenme disiplini" in prompt
    assert "20 dk yürüyüş" in prompt
    assert "Akşam meyve tabağı hazırla" in prompt
    assert "{plan_name}" not in prompt
    assert prompts.PROOF_VALIDATION_PROMPT.count("{plan_name}") == 1

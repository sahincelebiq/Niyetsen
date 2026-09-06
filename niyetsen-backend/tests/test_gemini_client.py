"""Gemini client — thinking config parity for text vs function-call paths."""
from __future__ import annotations

import asyncio

from app.core import gemini_client


def test_thinking_config_none_when_not_disabled():
    assert gemini_client._thinking_config_for("gemini-3.1-pro-preview", False) is None
    assert gemini_client._thinking_config_for("gemini-2.5-flash", False) is None


def test_thinking_config_gemini3_uses_level_low():
    cfg = gemini_client._thinking_config_for("gemini-3.1-pro-preview", True)
    assert cfg is not None
    level = getattr(cfg, "thinking_level", None)
    assert str(level).casefold().endswith("low")


def test_thinking_config_flash_uses_budget_zero():
    cfg = gemini_client._thinking_config_for("gemini-2.5-flash", True)
    assert cfg is not None
    assert getattr(cfg, "thinking_budget", None) == 0


def test_function_calls_apply_thinking_and_rebuild_on_fallback(monkeypatch):
    captured: list[tuple[str, object]] = []

    class FakeResp:
        function_calls = []

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            captured.append((model, config))
            if str(model).startswith("gemini-3"):
                raise RuntimeError("Model not found: 404")
            return FakeResp()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gemini_client, "get_client", lambda: FakeClient())
    monkeypatch.setattr(gemini_client.settings, "GEMINI_MAX_RETRIES", 1)
    # Default GEMINI_MODEL == GEMINI_MODEL_PLAN (both 3.1-pro-preview), so
    # isolate the chat/tool fallback path from the plan fallback (2.5-pro).
    monkeypatch.setattr(
        gemini_client.settings, "GEMINI_MODEL_PLAN", "gemini-3.1-pro-preview-plan"
    )
    monkeypatch.setattr(
        gemini_client.settings, "GEMINI_FALLBACK_MODEL", "gemini-2.5-flash"
    )

    result = asyncio.run(
        gemini_client.generate_function_calls(
            "mazeret",
            declarations=[],
            model="gemini-3.1-pro-preview",
            max_retries=1,
            disable_thinking=True,
        )
    )

    assert result == []
    assert len(captured) >= 2
    first_model, first_config = captured[0]
    second_model, second_config = captured[1]
    assert first_model.startswith("gemini-3")
    assert second_model == "gemini-2.5-flash"
    first_level = getattr(first_config.thinking_config, "thinking_level", None)
    assert str(first_level).casefold().endswith("low")
    assert getattr(second_config.thinking_config, "thinking_budget", None) == 0

"""
Niyetsen — Gemini İstemcisi
Tek sorumluluk: modele dayanıklı çağrı. Retry + backoff burada; iş mantığı
servislerde. İstemci LAZY kurulur ki testler API anahtarı olmadan koşsun.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from app.config import settings

log = logging.getLogger("niyetsen.gemini")

_client = None


def get_client():
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY tanımlı değil. .env.example'ı .env olarak kopyala "
                "ve gerçek anahtarı ORAYA yaz (koda değil)."
            )
        from google import genai  # lazy import: anahtar yoksa da app import edilebilsin
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


class GeminiUnavailable(Exception):
    """Retry'lar tükendi. Kullanıcıya nazik mesajı routes katmanı verir."""


def _strip_json_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```")[1] if "```" in t[3:] else t[3:]
        t = t.removeprefix("json").strip()
    return t


def _resolve_model(model: Optional[str]) -> str:
    return model or settings.GEMINI_MODEL


async def generate_text(
    contents: Any,
    system_instruction: Optional[str] = None,
    force_json: bool = False,
    *,
    model: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    max_retries: Optional[int] = None,
    response_schema: Optional[dict] = None,
    disable_thinking: bool = False,
    timeout_sec: Optional[float] = None,
) -> str:
    """
    Dayanıklı çağrı: settings.GEMINI_MAX_RETRIES kez exponential backoff.
    contents: str | list (google-genai formatında parça listesi — vision dahil).
    timeout_sec: MASTER_PLAN §1.9 — chat 30 sn, plan 90 sn. Verilmezse
    GEMINI_TIMEOUT_SEC uygulanır; takılan istek worker'ı süresiz bloklayamaz.
    """
    from google.genai import types

    resolved_model = _resolve_model(model)
    retry_limit = settings.GEMINI_MAX_RETRIES if max_retries is None else max_retries
    resolved_timeout = timeout_sec or settings.GEMINI_TIMEOUT_SEC
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json" if force_json else None,
    }
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    if force_json and response_schema is not None:
        config_kwargs["response_schema"] = response_schema
    if disable_thinking:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    config = types.GenerateContentConfig(**config_kwargs)

    client = get_client()

    last_err: Exception | None = None
    for attempt in range(retry_limit + 1):
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=contents,
                    config=config,
                ),
                timeout=resolved_timeout,
            )
            return resp.text or ""
        except Exception as e:  # noqa: BLE001 — SDK sürümüne göre hata tipleri değişir
            last_err = e
            if attempt >= retry_limit:
                break
            wait = min(2 ** attempt, 4)
            log.warning(
                "Gemini hatası (%s, deneme %s): %s — %ss bekleniyor",
                resolved_model,
                attempt + 1,
                e,
                wait,
            )
            await asyncio.sleep(wait)

    raise GeminiUnavailable(str(last_err))


async def generate_json(
    contents: Any,
    system_instruction: Optional[str] = None,
    *,
    model: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    max_retries: Optional[int] = None,
    json_retries: int = 2,
    response_schema: Optional[dict] = None,
    disable_thinking: bool = False,
    timeout_sec: Optional[float] = None,
) -> dict:
    """JSON zorla + güvenli parse. Bozuk JSON'da sınırlı tekrar."""
    last_raw = ""
    for _ in range(max(1, json_retries)):
        raw = await generate_text(
            contents,
            system_instruction=system_instruction,
            force_json=True,
            model=model,
            max_output_tokens=max_output_tokens,
            max_retries=max_retries,
            response_schema=response_schema,
            disable_thinking=disable_thinking,
            timeout_sec=timeout_sec,
        )
        last_raw = raw
        try:
            return json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            log.warning("Gemini bozuk JSON döndürdü, tekrar deneniyor: %.200s", raw)
    raise GeminiUnavailable(f"Model geçerli JSON üretemedi: {last_raw[:200]}")


async def generate_function_calls(
    contents: Any,
    declarations: list[dict],
    system_instruction: Optional[str] = None,
    *,
    model: Optional[str] = None,
) -> list[dict]:
    """Return native Gemini function calls without executing model-selected code."""
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="AUTO")
        ),
        max_output_tokens=256,
    )
    client = get_client()
    resolved_model = _resolve_model(model)
    last_err: Exception | None = None
    for attempt in range(settings.GEMINI_MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.GEMINI_TIMEOUT_SEC,
            )
            return [
                {"name": call.name, "args": dict(call.args or {})}
                for call in (response.function_calls or [])
            ]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt >= settings.GEMINI_MAX_RETRIES:
                break
            await asyncio.sleep(min(2 ** attempt, 4))
    raise GeminiUnavailable(str(last_err))


async def generate_json_with_image(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    *,
    model: Optional[str] = None,
) -> dict:
    """Vision çağrısı (kanıt doğrulama)."""
    from google.genai import types

    parts = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt,
    ]
    return await generate_json(
        parts,
        model=model,
        max_output_tokens=256,
        json_retries=1,
        max_retries=1,
    )

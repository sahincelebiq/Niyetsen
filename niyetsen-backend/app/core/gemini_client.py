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


async def generate_text(
    contents: Any,
    system_instruction: Optional[str] = None,
    force_json: bool = False,
) -> str:
    """
    Dayanıklı çağrı: settings.GEMINI_MAX_RETRIES kez exponential backoff.
    contents: str | list (google-genai formatında parça listesi — vision dahil).
    async: retry beklemesi asyncio.sleep ile yapılır ve asıl (senkron) SDK
    çağrısı asyncio.to_thread'e taşınır — event loop'u bloklamaz (bu fonksiyon
    async çağrı zincirinde: routes -> services -> buraya kadar await'lidir).
    """
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json" if force_json else None,
    )

    client = get_client()  # anahtar eksikse retry'a girmeden NET hata ver

    last_err: Exception | None = None
    for attempt in range(settings.GEMINI_MAX_RETRIES + 1):
        try:
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            return resp.text or ""
        except Exception as e:  # noqa: BLE001 — SDK sürümüne göre hata tipleri değişir
            last_err = e
            wait = 2 ** attempt
            log.warning("Gemini hatası (deneme %s): %s — %ss bekleniyor", attempt + 1, e, wait)
            await asyncio.sleep(wait)

    raise GeminiUnavailable(str(last_err))


async def generate_json(
    contents: Any,
    system_instruction: Optional[str] = None,
) -> dict:
    """JSON zorla + güvenli parse. Bozuk JSON'da bir kez daha dener."""
    for _ in range(2):
        raw = await generate_text(contents, system_instruction=system_instruction, force_json=True)
        try:
            return json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            log.warning("Gemini bozuk JSON döndürdü, tekrar deneniyor: %.200s", raw)
    raise GeminiUnavailable("Model geçerli JSON üretemedi")


async def generate_json_with_image(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
) -> dict:
    """Vision çağrısı (kanıt doğrulama, v2'de kahve/el falı da burayı kullanır)."""
    from google.genai import types

    parts = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt,
    ]
    return await generate_json(parts)

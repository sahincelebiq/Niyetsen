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


def _error_text(exc: Exception) -> str:
    return str(exc).casefold()


def _is_retryable(exc: Exception) -> bool:
    text = _error_text(exc)
    if "invalid_argument" in text and (
        "image" in text or "process input" in text or "unable to process" in text
    ):
        return False
    if "permission_denied" in text or "api key" in text or "api_key" in text:
        return False
    return True


def _strip_json_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("```")[1] if "```" in t[3:] else t[3:]
        t = t.removeprefix("json").strip()
    return t


def _resolve_model(model: Optional[str]) -> str:
    return model or settings.GEMINI_MODEL


def _is_model_unavailable(exc: Exception) -> bool:
    """Model adı geçersiz/erişilemez mi? (FAZ 8: Gemini 3 geçiş güvencesi).

    Yeni nesil model adı yanlış yazılır ya da hesapta henüz açık olmazsa
    istekler kalıcı hata verir; bu durumda fallback modele düşülür.
    """
    text = str(exc).lower()
    return any(marker in text for marker in (
        "not found", "not_found", "does not exist", "is not supported",
        "invalid model", "unknown model", "was not found", "permission denied",
        "404",
    ))


def _fallback_for(resolved_model: str) -> Optional[str]:
    """Kullanılan modele uygun fallback (plan→plan fallback'i, diğer→genel)."""
    if resolved_model == settings.GEMINI_MODEL_PLAN:
        fallback = settings.GEMINI_FALLBACK_MODEL_PLAN
    else:
        fallback = settings.GEMINI_FALLBACK_MODEL
    return fallback if fallback and fallback != resolved_model else None


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
    timeout_sec: Optional[int] = None,
) -> str:
    """
    Dayanıklı çağrı: settings.GEMINI_MAX_RETRIES kez exponential backoff.
    contents: str | list (google-genai formatında parça listesi — vision dahil).
    timeout_sec: deneme başına zaman aşımı (plan gibi uzun işler için yükseltilir).
    """
    from google.genai import types

    resolved_model = _resolve_model(model)
    retry_limit = settings.GEMINI_MAX_RETRIES if max_retries is None else max_retries
    attempt_timeout = timeout_sec or settings.GEMINI_TIMEOUT_SEC
    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
        "response_mime_type": "application/json" if force_json else None,
    }
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    if force_json and response_schema is not None:
        config_kwargs["response_schema"] = response_schema
    def _build_config(for_model: str) -> "types.GenerateContentConfig":
        kwargs = dict(config_kwargs)
        if disable_thinking:
            # Gemini 3 ailesi thinking_budget=0 kabul ETMEZ (Pro'da düşünme
            # tamamen kapatılamaz); en hızlı geçerli ayar thinking_level="low".
            # 2.5 ve öncesi eski yolu kullanır. Fallback'te aile değişirse
            # config yeniden kurulur (aksi halde 400 INVALID_ARGUMENT).
            if for_model.startswith("gemini-3"):
                kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="low")
            else:
                kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        return types.GenerateContentConfig(**kwargs)

    config = _build_config(resolved_model)

    client = get_client()

    last_err: Exception | None = None
    for attempt in range(retry_limit + 1):
        try:
            # Takılan tek bir SDK çağrısı tüm isteği süresiz bekletmesin:
            # her deneme GEMINI_TIMEOUT_SEC ile sınırlanır (mobil istemcinin
            # sohbet zaman aşımıyla uyumlu üst sınır).
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=contents,
                    config=config,
                ),
                timeout=attempt_timeout,
            )
            return resp.text or ""
        except asyncio.TimeoutError as e:
            last_err = e
            if attempt >= retry_limit:
                break
            log.warning(
                "Gemini zaman aşımı (%s, deneme %s): %ss sınırı aşıldı",
                resolved_model,
                attempt + 1,
                attempt_timeout,
            )
            continue
        except Exception as e:  # noqa: BLE001 — SDK sürümüne göre hata tipleri değişir
            last_err = e
            # FAZ 8: model adı geçersizse (Gemini 3 geçişinde yanlış string vb.)
            # beklemeden fallback modele geç — kullanıcı hata görmez.
            if _is_model_unavailable(e):
                fallback = _fallback_for(resolved_model)
                if fallback:
                    log.warning(
                        "Model erişilemez (%s) — fallback'e geçiliyor: %s",
                        resolved_model, fallback,
                    )
                    resolved_model = fallback
                    config = _build_config(resolved_model)
                    continue
            if not _is_retryable(e):
                break
            if attempt >= retry_limit:
                break
            wait = min(2 ** attempt, 8)
            log.warning(
                "Gemini hatası (%s, deneme %s): %s — %ss bekleniyor",
                resolved_model,
                attempt + 1,
                e,
                wait,
            )
            await asyncio.sleep(wait)

    if last_err is not None and not _is_retryable(last_err):
        raise GeminiUnavailable(str(last_err))
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
    timeout_sec: Optional[int] = None,
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
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=resolved_model,
                contents=contents,
                config=config,
            )
            return [
                {"name": call.name, "args": dict(call.args or {})}
                for call in (response.function_calls or [])
            ]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if not _is_retryable(exc):
                break
            if attempt >= settings.GEMINI_MAX_RETRIES:
                break
            await asyncio.sleep(min(2 ** attempt, 8))
    raise GeminiUnavailable(str(last_err))


PROOF_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {"type": "boolean"},
        "confidence": {"type": "integer"},
        "reason": {"type": "string"},
    },
    "required": ["matches", "confidence", "reason"],
}


async def generate_json_with_images(
    prompt: str,
    images: list[tuple[bytes, str]],
    *,
    model: Optional[str] = None,
    response_schema: Optional[dict] = None,
    max_output_tokens: int = 256,
) -> dict:
    """Çoklu görselli vision çağrısı (faz8.13/2d: kahve falı maks 3 foto).

    faz8.13 kök düzeltmesi: response_schema önceden kanıt şemasına SABİTTİ —
    fal ve ek özeti çağrıları yanlış şemayla boş dönüyordu. Artık her çağrı
    kendi şemasını geçirir.
    """
    from google.genai import types

    parts: list = [
        types.Part.from_bytes(data=data, mime_type=mime)
        for data, mime in images
    ]
    parts.append(prompt)
    try:
        return await asyncio.wait_for(
            generate_json(
                parts,
                model=model,
                max_output_tokens=max_output_tokens,
                json_retries=2,
                max_retries=settings.GEMINI_MAX_RETRIES,
                response_schema=response_schema,
                disable_thinking=True,
            ),
            timeout=settings.GEMINI_PROOF_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError as exc:
        raise GeminiUnavailable(
            f"Görüntü {settings.GEMINI_PROOF_TIMEOUT_SEC}s içinde işlenemedi."
        ) from exc


async def generate_json_with_image(
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    *,
    model: Optional[str] = None,
    response_schema: Optional[dict] = None,
    max_output_tokens: int = 256,
) -> dict:
    """Tek görselli vision çağrısı (kanıt doğrulama, ek özeti, fal)."""
    return await generate_json_with_images(
        prompt,
        [(image_bytes, mime_type)],
        model=model,
        response_schema=response_schema,
        max_output_tokens=max_output_tokens,
    )


async def generate_image_bytes(
    prompt: str,
    *,
    model: str | None = None,
) -> tuple[bytes, str]:
    """Nano Banana (gemini-2.5-flash-image) ile plan görseli üretir."""
    from google.genai import types

    resolved_model = model or settings.GEMINI_MODEL_IMAGE
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE"],
    )
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(settings.GEMINI_MAX_RETRIES + 1):
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=resolved_model,
                    contents=prompt,
                    config=config,
                ),
                timeout=settings.GEMINI_IMAGE_TIMEOUT_SEC,
            )
            candidates = getattr(resp, "candidates", None) or []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        mime = getattr(inline, "mime_type", None) or "image/png"
                        return inline.data, mime
            raise GeminiUnavailable("Model görsel üretmedi (inline_data yok)")
        except asyncio.TimeoutError as exc:
            raise GeminiUnavailable(
                f"Görsel üretimi {settings.GEMINI_IMAGE_TIMEOUT_SEC}s içinde tamamlanamadı."
            ) from exc
        except GeminiUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if not _is_retryable(exc):
                break
            if attempt >= settings.GEMINI_MAX_RETRIES:
                break
            await asyncio.sleep(min(2 ** attempt, 8))
    if last_err is not None and not _is_retryable(last_err):
        raise GeminiUnavailable(str(last_err))
    raise GeminiUnavailable(str(last_err))

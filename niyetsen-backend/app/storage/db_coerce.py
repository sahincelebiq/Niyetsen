"""PostgREST satırlarını güvenli parse — jsonb dict/str, unique ihlali."""
from __future__ import annotations

import json
from typing import Any


def is_unique_violation(exc: BaseException) -> bool:
    """Postgres 23505 — eşzamanlı plan/kullanıcı insert yarışı."""
    code = getattr(exc, "code", None)
    if str(code) == "23505":
        return True
    text = str(exc).casefold()
    return (
        "23505" in text
        or "duplicate key" in text
        or "unique constraint" in text
        or "uniqueviolation" in text
    )


def parse_json_object(value: Any) -> dict:
    """jsonb bazen dict, bazen JSON string (çift encode) gelir.

    `json.loads(dict)` TypeError atar — mistik hafıza sessizce boşalıyordu.
    """
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}

"""ISO / timestamptz değerlerini datetime'a çevir — PostgREST çoğu zaman str döner."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


def coerce_datetime(value: Any) -> datetime | None:
    """Supabase timestamptz, ISO string veya naive datetime → tz-aware UTC.

    Canlı 500: `'str' object has no attribute 'astimezone'` — PostgREST
    `trial_started_at` alanını datetime değil string verir.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

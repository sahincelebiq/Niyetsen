"""ISO / timestamptz değerlerini datetime/date'e çevir — PostgREST çoğu zaman str döner."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Europe/Istanbul"


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


def coerce_date(value: Any) -> date | None:
    """date / datetime / timestamptz str → takvim günü.

    `isinstance(datetime, date)` True'dur; datetime'ı olduğu gibi döndürmek
    `last_active_date == day` karşılaştırmasını her zaman False yapar.
    `date.fromisoformat('2026-08-10T00:00:00+00:00')` ValueError atar.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = coerce_datetime(value)
    return parsed.date() if parsed is not None else None


def local_today(timezone_name: str, *, now: datetime | None = None) -> date:
    """Kullanıcı timezone'unda bugün. Geçersiz isim → Europe/Istanbul."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    try:
        zone = ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    return current.astimezone(zone).date()

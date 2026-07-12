"""Saat dilimine göre kişiselleştirilmiş sohbet karşılama metni."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _resolve_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name or "Europe/Istanbul")
    except ZoneInfoNotFoundError:
        return ZoneInfo("Europe/Istanbul")


def _salutation_for_hour(hour: int) -> str:
    if 5 <= hour < 12:
        return "Günaydın"
    if 12 <= hour < 18:
        return "İyi günler"
    return "İyi akşamlar"


def build_chat_greeting(*, name: str | None, timezone_name: str) -> str:
    local_now = datetime.now(timezone.utc).astimezone(_resolve_timezone(timezone_name))
    salutation = _salutation_for_hour(local_now.hour)
    trimmed = (name or "").strip()
    opener = f"{salutation} {trimmed}!" if trimmed else f"{salutation}!"
    return (
        f"{opener} 🌙 Ben Niyetsen. Bu yılı nasıl geçirmek istediğini birlikte "
        "konuşalım — hangi şehirdesin, neyle vakit geçirmeyi seviyorsun, "
        "haftada ne kadar zamanın var?"
    )

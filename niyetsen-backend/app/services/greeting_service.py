"""Saat dilimine ve kullanıcı bağlamına göre kişiselleştirilmiş sohbet karşılama."""
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


def _name_clause(name: str | None) -> str:
    trimmed = (name or "").strip()
    return f" {trimmed}" if trimmed else ""


def build_chat_greeting(
    *,
    name: str | None,
    timezone_name: str,
    streak_len: int = 0,
    pending_tasks_today: int = 0,
    active_plan_name: str = "",
    has_plan: bool = False,
) -> str:
    """KULLANICI BELLEĞİ'nin sohbet girişine yansıması — zincir + bugün nabzı."""
    local_now = datetime.now(timezone.utc).astimezone(_resolve_timezone(timezone_name))
    salutation = _salutation_for_hour(local_now.hour)
    opener = f"{salutation}{_name_clause(name)}!"

    if has_plan and streak_len > 0 and pending_tasks_today > 0:
        plan_hint = f" ({active_plan_name})" if active_plan_name.strip() else ""
        return (
            f"{opener} 🌙 {streak_len} günlük zincirin devam ediyor — "
            f"bugün{plan_hint} {pending_tasks_today} görev seni bekliyor. "
            "Hazırsan küçük bir adımla başlayalım; takıldığın yerde buradayım."
        )

    if has_plan and streak_len > 0:
        return (
            f"{opener} 🌙 {streak_len} günlük zincirin hâlâ yanında. "
            "Bugün için bekleyen görev görünmüyor — istersen sohbet edelim veya "
            "yeni bir adım planlayalım."
        )

    if has_plan and pending_tasks_today > 0:
        plan_hint = f" ({active_plan_name})" if active_plan_name.strip() else ""
        return (
            f"{opener} 🌙 Bugün{plan_hint} {pending_tasks_today} görev hazır. "
            "İlk küçük halkayı birlikte seçebiliriz — nasıl hissediyorsun?"
        )

    if has_plan:
        return (
            f"{opener} 🌙 Planın hazır; bugün için görev görünmüyor. "
            "İstersen sohbetten yeni bir adım ekleyebilir veya planını gözden geçirebiliriz."
        )

    return (
        f"{opener} 🌙 Ben Niyetsen. Bu yılı nasıl geçirmek istediğini birlikte "
        "konuşalım — hangi şehirdesin, neyle vakit geçirmeyi seviyorsun, "
        "haftada ne kadar zamanın var?"
    )

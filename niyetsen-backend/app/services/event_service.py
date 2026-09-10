"""Kök plan içi etkinlikler — 365 tasks'ten ayrı, fotosuz Yaptım.

Kurallar (spec 2026-09-10):
- Tek seferlik + tekrarlayan (none/daily/weekdays/weekly+byweekday).
- Yaptım = beyan, +50 kategori puanı, zincir kurtarabilir; ceza YOK.
- Occurrence materialize `GET /tasks/daily` içinde (bugün için).
- Hata etkinlikte kalır: Bugün akışı etkinlik yüzünden DÜŞMEZ (degrade).
"""
from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from datetime import date, datetime, timezone

from app.config import CATEGORIES
from app.models.schemas import (
    Category,
    DailyEventItem,
    PlanEvent,
    PlanEventOccurrence,
    is_valid_clock,
)
from app.services import scoring_service
from app.storage.base import Repository

log = logging.getLogger("niyetsen.events")

RECURRENCES = ("none", "daily", "weekdays", "weekly")
MAX_DURATION_MIN = 240
COMPLETION_REASON = "etkinlik tamamlandı"

# Kısa/çok anlamlı kökler ("ara", "uyu") kelime sınırıyla eşleşir; aksi hâlde
# "para biriktir" Sosyallik, "uyum" Özsaygı sayılıyordu.
_WORD_NEEDLES = {"ara", "uyu", "spor", "oku"}

_CATEGORY_RULES: list[tuple[tuple[str, ...], list[Category]]] = [
    (
        ("şınav", "sinav", "push-up", "pushup", "spor", "koş", "kosu",
         "egzersiz", "fitness", "antrenman", "yürüyüş", "yuruyus", "yoga",
         "plank", "squat", "mekik", "bisiklet", "yüzme", "yuzme"),
        ["İrade", "Disiplin"],
    ),
    (("uyu", "uyku", "dinlen", "erken yat", "uyku saati", "şekerleme"), ["Özsaygı"]),
    (("meditasyon", "nefes", "journal", "günlük yaz", "şükran", "sukran"), ["Özsaygı", "İstikrar"]),
    (("ara", "buluş", "bulus", "sohbet et", "mesaj at", "görüş", "gorus", "ziyaret"), ["Sosyallik"]),
    (("kitap", "oku", "ders", "çalış", "calis", "kurs", "tekrar et", "pratik"), ["Disiplin", "İstikrar"]),
    (("su iç", "su ic", "vitamin", "sebze", "meyve", "sağlıklı", "saglikli"), ["Özsaygı", "İrade"]),
    (("sunum", "sahne", "konuş", "konus", "başvur", "basvur"), ["Özgüven"]),
]


class EventError(ValueError):
    pass


class EventNotFound(EventError):
    pass


class EventAlreadyDone(EventError):
    pass


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").casefold()


def _needle_hit(folded: str, needle: str) -> bool:
    if needle in _WORD_NEEDLES:
        return re.search(rf"(?<![\w]){re.escape(needle)}(?![\wçğıöşü])", folded) is not None
    return needle in folded


def infer_categories(title: str) -> list[Category]:
    folded = _fold(title)
    for needles, cats in _CATEGORY_RULES:
        if any(_needle_hit(folded, n) for n in needles):
            return list(cats)
    return ["İstikrar"]


def occurs_on(event: PlanEvent, day: date) -> bool:
    if day < event.start_date:
        return False
    if event.end_date is not None and day > event.end_date:
        return False
    if event.recurrence == "none":
        return day == event.start_date
    if event.recurrence == "daily":
        return True
    if event.recurrence == "weekdays":
        return day.weekday() < 5
    weekdays = event.byweekday or [event.start_date.weekday()]
    return day.weekday() in weekdays


def _valid_categories(raw: list[str] | None) -> list[Category]:
    picked: list[str] = []
    for c in raw or []:
        if c in CATEGORIES and c not in picked:
            picked.append(c)
    return picked  # type: ignore[return-value]


def _clean_weekdays(raw: list[int] | None) -> list[int]:
    cleaned: set[int] = set()
    for value in raw or []:
        try:
            day = int(value)
        except (TypeError, ValueError) as exc:
            raise EventError("Haftanın günleri 0 (Pzt) ile 6 (Paz) arasında olmalı.") from exc
        if day < 0 or day > 6:
            raise EventError("Haftanın günleri 0 (Pzt) ile 6 (Paz) arasında olmalı.")
        cleaned.add(day)
    return sorted(cleaned)


def create_event(
    repository: Repository,
    user_id: str,
    *,
    plan_id: str,
    title: str,
    scheduled_time: str,
    start_date: date,
    recurrence: str = "none",
    end_date: date | None = None,
    byweekday: list[int] | None = None,
    categories: list[str] | None = None,
    duration_min: int = 15,
    created_by: str = "user",
    today: date | None = None,
) -> PlanEvent:
    """Etkinliği yazar ve (varsa) BUGÜNÜN occurrence'ını açar.

    `today` kullanıcı yerel günüdür; verilmezse start_date sayılır. Gelecek
    başlangıçlı etkinlik bugün occurrence ÜRETMEZ — Yaptım erken basılamaz.
    """
    if not repository.plan_belongs_to_user(user_id, plan_id):
        raise EventNotFound("Plan bulunamadı.")
    cleaned = " ".join((title or "").split())
    if not cleaned:
        raise EventError("Etkinlik başlığı gerekli.")
    if len(cleaned) > 200:
        cleaned = cleaned[:200].rstrip()
    if not is_valid_clock(scheduled_time or ""):
        raise EventError("Saat HH:MM biçiminde (00:00–23:59) olmalı.")
    if recurrence not in RECURRENCES:
        raise EventError("Geçersiz tekrar kuralı.")
    if end_date is not None and end_date < start_date:
        raise EventError("Bitiş tarihi başlangıçtan önce olamaz.")
    try:
        duration = int(duration_min)
    except (TypeError, ValueError) as exc:
        raise EventError("Süre dakika cinsinden sayı olmalı.") from exc
    duration = min(max(duration, 1), MAX_DURATION_MIN)
    weekdays = _clean_weekdays(byweekday)
    if recurrence == "weekly" and not weekdays:
        weekdays = [start_date.weekday()]
    if recurrence != "weekly":
        weekdays = []
    cats = _valid_categories(categories) or infer_categories(cleaned)
    event = PlanEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        plan_id=plan_id,
        title=cleaned,
        categories=cats,
        scheduled_time=scheduled_time,
        duration_min=duration,
        recurrence=recurrence,  # type: ignore[arg-type]
        byweekday=weekdays,
        start_date=start_date,
        end_date=end_date,
        created_by="agent" if created_by == "agent" else "user",
    )
    repository.save_plan_event(event)
    if today is None:
        today = start_date
    if occurs_on(event, today):
        occ = repository.ensure_event_occurrence(event, today)
        event.occurrences = [occ]
    return event


def delete_event(repository: Repository, user_id: str, event_id: str) -> None:
    """Etkinliği ve occurrence'larını siler (tamamlanmış puanlar point_log'da kalır)."""
    if not repository.delete_plan_event(user_id, event_id):
        raise EventNotFound("Etkinlik bulunamadı.")


def materialize_for_date(
    repository: Repository, user_id: str, day: date
) -> None:
    for event in repository.list_plan_events(user_id):
        if not occurs_on(event, day):
            continue
        repository.ensure_event_occurrence(event, day)


def list_daily_events(
    repository: Repository, user_id: str, day: date
) -> list[DailyEventItem]:
    """Bugünün etkinlik kalemleri. Etkinlik altyapısı hata verirse boş liste —
    Bugün sekmesi 365 görevleriyle açılmaya devam eder (degrade kuralı)."""
    try:
        materialize_for_date(repository, user_id, day)
        occurrences = repository.list_event_occurrences_for_date(user_id, day)
        if not occurrences:
            return []
        events_by_id = {
            event.id: event for event in repository.list_plan_events(user_id)
        }
        names = {
            item.id: item.name for item in repository.list_plan_summaries(user_id)
        }
    except Exception:  # noqa: BLE001 — etkinlik hatası Bugün'ü düşürmez
        log.warning("Etkinlik listesi okunamadı (yoksayıldı)", exc_info=True)
        return []
    items: list[DailyEventItem] = []
    for occ in occurrences:
        event = events_by_id.get(occ.event_id)
        if event is None:
            continue
        items.append(
            DailyEventItem(
                occurrence_id=occ.id,
                event_id=event.id,
                plan_id=event.plan_id,
                plan_name=names.get(event.plan_id, ""),
                title=event.title,
                categories=event.categories,
                scheduled_time=event.scheduled_time,
                duration_min=event.duration_min,
                status=occ.status,
                recurrence=event.recurrence,
            )
        )
    items.sort(key=lambda item: (item.status == "done", item.scheduled_time))
    return items


def complete_occurrence(
    repository: Repository,
    user_id: str,
    occurrence_id: str,
    *,
    today: date | None = None,
) -> list:
    """Beyanla Yaptım: +50 kategori puanı. Gelecek güne erken basılamaz;
    çift dokunuş (yarış) ikinci kez puan vermez."""
    occ = repository.get_event_occurrence(user_id, occurrence_id)
    if occ is None:
        raise EventNotFound("Etkinlik bulunamadı.")
    if occ.status == "done":
        raise EventAlreadyDone("Bu etkinlik zaten tamamlandı.")
    if today is not None and occ.date > today:
        raise EventError("Bu etkinliğin günü henüz gelmedi.")
    event = repository.get_plan_event(user_id, occ.event_id)
    if event is None:
        raise EventNotFound("Etkinlik bulunamadı.")
    completed_at = datetime.now(timezone.utc)
    if not repository.mark_event_occurrence_done(user_id, occ.id, completed_at):
        raise EventAlreadyDone("Bu etkinlik zaten tamamlandı.")
    state = repository.get_state(user_id)
    events = [
        row.model_copy(update={"reason": COMPLETION_REASON})
        for row in scoring_service.complete_task(state, list(event.categories))
    ]
    repository.save_state(state)
    repository.append_point_log(user_id, occ.id, events)
    return events


_RECURRENCE_TR = {
    "none": "tek sefer",
    "daily": "her gün",
    "weekdays": "hafta içi",
    "weekly": "haftalık",
}


def describe_plan_for_agent(
    repository: Repository, user_id: str, plan_id: str, today: date
) -> tuple[str, str]:
    """Plan-içi ajan için HEDEF planın bugünü + etkinlikleri (aktif plan değil).

    Dönüş: (today_status, events_line) — KULLANICI BELLEĞİ satırları.
    """
    plan = repository.get_plan_by_id(user_id, plan_id)
    plan_name = plan.name if plan else ""
    plan_bit = f"Plan «{plan_name}». " if plan_name else ""
    if plan is not None:
        plan_day = (today - plan.start_date).days + 1
        if plan_day >= 1:
            plan_bit += f"Plan günü {plan_day}/{plan.duration_days}. "
    todays = [
        item.task
        for item in repository.list_daily_tasks_for_date(user_id, today)
        if item.plan_id == plan_id
    ]
    if todays:
        titles = "; ".join(f"{t.title} [{t.status}]" for t in todays[:6])
        today_status = f"{plan_bit}Bugünün 365 görevleri: {titles}"
    else:
        today_status = f"{plan_bit}Bugüne atanmış 365 görevi yok"

    events = repository.list_plan_events(user_id, plan_id)
    if not events:
        events_line = "Bu planda etkinlik yok."
    else:
        occ_status = {
            occ.event_id: occ.status
            for occ in repository.list_event_occurrences_for_date(user_id, today)
        }
        parts = []
        for event in events[:10]:
            status = occ_status.get(event.id)
            suffix = f" — bugün {status}" if status else ""
            parts.append(
                f"{event.title} ({_RECURRENCE_TR.get(event.recurrence, event.recurrence)} "
                f"{event.scheduled_time}){suffix}"
            )
        events_line = "Plan etkinlikleri: " + "; ".join(parts)
    return today_status, events_line

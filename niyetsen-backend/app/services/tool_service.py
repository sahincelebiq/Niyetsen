"""Allowlisted chat tool dispatcher.

The model may request an action, but only this module decides whether it is
valid and which server-side mutation is allowed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date

from app.config import CATEGORIES, settings
from app.core import tools
from app.models.schemas import PlanDay, Task, ToolCall
from app.services import task_lifecycle_service
from app.services.plan_edit_service import cover_for_manual_task
from app.storage.base import Repository

log = logging.getLogger("niyetsen.tools")


def _owned_task(repository: Repository, user_id: str, task_id: object) -> Task:
    task = repository.get_task(user_id, str(task_id or ""))
    if task is None:
        raise ValueError("Bu görev bulunamadı veya sana ait değil.")
    return task


def _normalize_clock(raw: str) -> str:
    """'9.00' / '9:5' → '09:00' / '09:05'. Bozuk metin olduğu gibi kalır."""
    text = (raw or "").strip()
    if ":" not in text and "." in text:
        text = text.replace(".", ":")
    pieces = text.split(":")
    if len(pieces) == 2 and pieces[0].isdigit() and pieces[1].isdigit():
        return f"{int(pieces[0]):02d}:{int(pieces[1]):02d}"
    return text


def _create_task(
    repository: Repository,
    user_id: str,
    args: dict,
    *,
    today: date | None = None,
) -> str:
    plan = repository.get_plan(user_id)
    if plan is None:
        raise ValueError("Yeni görev eklemek için önce aktif bir plan gerekli.")
    title = str(args.get("title") or "").strip()
    tiny_version = str(args.get("tiny_version") or "").strip()
    try:
        task_date = date.fromisoformat(str(args.get("date") or ""))
    except ValueError as exc:
        raise ValueError("Görev tarihi YYYY-MM-DD biçiminde olmalı.") from exc
    categories: list[str] = []
    for category in args.get("categories") or []:
        name = str(category)
        if name in CATEGORIES and name not in categories:
            categories.append(name)
    if not title or not categories:
        raise ValueError("Görev başlığı ve en az bir geçerli kategori gerekli.")
    anchor = today or date.today()
    if task_date < anchor:
        raise ValueError("Geçmiş güne görev eklenemez.")
    day_no = (task_date - plan.start_date).days + 1
    if day_no < 1 or day_no > plan.duration_days:
        raise ValueError("Görev tarihi aktif planın dışında.")
    plan_day = next((day for day in plan.days if day.day == day_no), None)
    if plan_day is None:
        plan_day = PlanDay(day=day_no, theme="", tasks=[])
        plan.days.append(plan_day)
        plan.days.sort(key=lambda day: day.day)
    if len(plan_day.tasks) >= settings.MAX_TASKS_PER_DAY:
        raise ValueError("Bu gün için görev sınırına ulaşıldı.")
    cover = cover_for_manual_task(title, categories)
    plan_day.tasks.append(
        Task(
            id=str(uuid.uuid4()),
            day=day_no,
            date=task_date,
            title=title,
            categories=categories,
            image_keyword=title,
            image_url=cover.url,
            image_source=cover.source,
            image_attribution=cover.attribution,
            image_attribution_url=cover.attribution_url,
            tiny_version=tiny_version or "2 dakikalık en küçük adımla başla.",
        )
    )
    repository.save_plan(user_id, plan)
    return f"“{title}” görevi plana eklendi."


def _create_event(
    repository: Repository,
    user_id: str,
    plan_id: str,
    args: dict,
    today: date | None,
) -> str:
    """etkinlik_olustur — yalnız plan-içi ajan; 365 tasks'e DOKUNMAZ."""
    from app.services import event_service

    title = str(args.get("title") or "").strip()
    time_str = _normalize_clock(str(args.get("time") or "09:00"))
    raw_date = str(args.get("date") or "").strip()
    if raw_date:
        try:
            start = date.fromisoformat(raw_date[:10])
        except ValueError as exc:
            raise ValueError("Tarih YYYY-MM-DD olmalı.") from exc
    elif today is not None:
        start = today
    else:
        raise ValueError("Etkinlik için başlangıç tarihi gerekli.")
    if today is not None and start < today:
        # Model geçmiş bir yıl uydurduysa bugünden başlat — geçmişe etkinlik yok.
        start = today
    recurrence = str(args.get("recurrence") or "none").strip().lower()
    cats = args.get("categories") or []
    raw_weekdays = args.get("byweekday")
    # Model 7/9 gibi gün uydurursa etkinliği düşürme, geçersiz günü at.
    # 0 = Pazartesi; `or []` bunu boş sanıp başlangıç gününe düşürürdü.
    if raw_weekdays is None or raw_weekdays == "":
        raw_weekdays = []
    elif isinstance(raw_weekdays, bool):
        raw_weekdays = []
    elif isinstance(raw_weekdays, int):
        raw_weekdays = [raw_weekdays]
    elif isinstance(raw_weekdays, str):
        raw_weekdays = [part.strip() for part in raw_weekdays.split(",") if part.strip()]
    byweekday: list[int] = []
    if isinstance(raw_weekdays, list):
        for value in raw_weekdays:
            try:
                day_no = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= day_no <= 6:
                byweekday.append(day_no)
    duration = args.get("duration_min") or 15
    try:
        event = event_service.create_event(
            repository,
            user_id,
            plan_id=plan_id,
            title=title,
            scheduled_time=time_str,
            start_date=start,
            recurrence=recurrence,
            byweekday=byweekday,
            categories=[str(c) for c in cats] if isinstance(cats, list) else [],
            duration_min=int(duration) if isinstance(duration, (int, float)) else 15,
            created_by="agent",
            today=today or start,
        )
    except event_service.EventError as exc:
        # Model hatalı saat/tekrar üretti → kullanıcıya düz cümle, istisna yok.
        return f"Etkinlik eklenemedi: {exc}"
    when = {
        "none": start.strftime("%d.%m.%Y"),
        "daily": "her gün",
        "weekdays": "hafta içi her gün",
        "weekly": "haftalık",
    }.get(event.recurrence, "")
    return (
        f"“{event.title}” etkinliği plana eklendi — {when} {event.scheduled_time}. "
        "Bugün sekmesinde fotosuz “Yaptım” ile işaretleyebilirsin."
    )


def dispatch(
    repository: Repository,
    user_id: str,
    calls: list[ToolCall],
    *,
    plan_id: str | None = None,
    today: date | None = None,
) -> tuple[list[ToolCall], list[str]]:
    """Execute server tools and return device actions plus user-facing results."""
    device_actions: list[ToolCall] = []
    messages: list[str] = []
    for call in calls:
        if not tools.is_allowed(call.name):
            messages.append("Güvenlik nedeniyle bilinmeyen araç çağrısı reddedildi.")
            continue
        try:
            if call.name == "gorev_ertele_mazeretli":
                task = _owned_task(repository, user_id, call.args.get("task_id"))
                task_lifecycle_service.excuse_task(
                    repository, user_id, task.id
                )
                messages.append(
                    "Görev mazeretli olarak ertelendi; sabit −25 uygulandı "
                    "ve sessiz kaçırma sayacı sıfırlandı."
                )
            elif call.name == "gorev_olustur":
                messages.append(
                    _create_task(repository, user_id, call.args, today=today)
                )
            elif call.name == "etkinlik_olustur":
                if not plan_id:
                    # Global sohbette bu araç bildirilmez; model yine de çağırdıysa
                    # kullanıcıya teknik mesaj sızdırmadan yoksay.
                    log.info("etkinlik_olustur plan bağlamı dışında çağrıldı, yoksayıldı")
                    continue
                messages.append(
                    _create_event(repository, user_id, plan_id, call.args, today)
                )
            elif call.name == "kanit_dogrula":
                _owned_task(repository, user_id, call.args.get("task_id"))
                device_actions.append(call)
                messages.append("Kanıt için uygulama içi kamerayı açabilirsin.")
            elif call.name == "puan_guncelle":
                messages.append(
                    "Puan yalnız doğrulanmış kanıt, mazeret veya gün sonu "
                    "akışından güncellenebilir."
                )
            elif call.name in {"alarm_kur", "takvime_ekle"}:
                device_actions.append(call)
        except (
            ValueError,
            task_lifecycle_service.TaskLifecycleError,
        ) as exc:
            messages.append(str(exc))
    return device_actions, messages

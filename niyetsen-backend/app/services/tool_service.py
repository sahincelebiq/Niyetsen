"""Allowlisted chat tool dispatcher.

The model may request an action, but only this module decides whether it is
valid and which server-side mutation is allowed.
"""
from __future__ import annotations

import uuid
from datetime import date

from app.config import CATEGORIES, settings
from app.core import tools
from app.models.schemas import PlanDay, Task, ToolCall
from app.services import task_lifecycle_service
from app.storage.base import Repository


def _owned_task(repository: Repository, user_id: str, task_id: object) -> Task:
    task = repository.get_task(user_id, str(task_id or ""))
    if task is None:
        raise ValueError("Bu görev bulunamadı veya sana ait değil.")
    return task


def _create_task(
    repository: Repository,
    user_id: str,
    args: dict,
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
    categories = [
        str(category) for category in (args.get("categories") or [])
        if str(category) in CATEGORIES
    ]
    if not title or not categories:
        raise ValueError("Görev başlığı ve en az bir geçerli kategori gerekli.")
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
    plan_day.tasks.append(
        Task(
            id=str(uuid.uuid4()),
            day=day_no,
            date=task_date,
            title=title,
            categories=categories,
            tiny_version=tiny_version or "2 dakikalık en küçük adımla başla.",
        )
    )
    repository.save_plan(user_id, plan)
    return f"“{title}” görevi plana eklendi."


def dispatch(
    repository: Repository,
    user_id: str,
    calls: list[ToolCall],
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
                messages.append(_create_task(repository, user_id, call.args))
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

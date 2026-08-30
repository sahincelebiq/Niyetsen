"""FAZ 8.3 — plan görev düzenleme (taşı / düzenle / ekle / sil).

Kurallar (FAZ8_LANSMAN §8.3):
- Geçmiş güne taşınamaz / eklenemez.
- Tamamlanmış (pending dışı) görev düzenlenemez / silinemez.
- Silme ceza tetiklemez.
- Yalnız aktif plan; plans.id TEXT.
- Task şemasında time yok → title + date.
"""
from __future__ import annotations

import uuid
from datetime import date

from app.config import CATEGORIES, settings
from app.models.schemas import Category, Plan, PlanDay, Task
from app.storage.base import Repository


class PlanEditError(ValueError):
    pass


class TaskNotFound(PlanEditError):
    pass


class TaskNotEditable(PlanEditError):
    pass


class PlanNotFound(PlanEditError):
    pass


def _active_plan(repo: Repository, user_id: str) -> Plan:
    plan = repo.get_plan(user_id)
    if plan is None:
        raise PlanNotFound("Aktif plan bulunamadı.")
    return plan


def _find_task_in_plan(plan: Plan, task_id: str) -> tuple[PlanDay, Task]:
    for plan_day in plan.days:
        for task in plan_day.tasks:
            if task.id == task_id:
                return plan_day, task
    raise TaskNotFound("Görev bulunamadı.")


def _require_pending(task: Task) -> None:
    if task.status != "pending":
        raise TaskNotEditable("Tamamlanmış veya sonuçlanmış görev düzenlenemez.")


def _day_no_for_date(plan: Plan, task_date: date) -> int:
    day_no = (task_date - plan.start_date).days + 1
    if day_no < 1 or day_no > plan.duration_days:
        raise PlanEditError("Görev tarihi aktif planın dışında.")
    return day_no


def _ensure_plan_day(plan: Plan, day_no: int) -> PlanDay:
    plan_day = next((day for day in plan.days if day.day == day_no), None)
    if plan_day is None:
        plan_day = PlanDay(day=day_no, theme="", tasks=[])
        plan.days.append(plan_day)
        plan.days.sort(key=lambda day: day.day)
    return plan_day


def _count_tasks_on_day(plan: Plan, day_no: int, *, exclude_task_id: str | None = None) -> int:
    plan_day = next((day for day in plan.days if day.day == day_no), None)
    if plan_day is None:
        return 0
    return sum(1 for t in plan_day.tasks if t.id != exclude_task_id)


def _reject_past(task_date: date, *, today: date) -> None:
    if task_date < today:
        raise PlanEditError("Geçmiş güne görev taşınamaz veya eklenemez.")


def _move_task(plan: Plan, task: Task, from_day: PlanDay, new_date: date) -> None:
    new_day_no = _day_no_for_date(plan, new_date)
    if (
        _count_tasks_on_day(plan, new_day_no, exclude_task_id=task.id)
        >= settings.MAX_TASKS_PER_DAY
    ):
        raise PlanEditError("Bu gün için görev sınırına ulaşıldı.")
    if from_day.day != new_day_no:
        from_day.tasks = [t for t in from_day.tasks if t.id != task.id]
        if not from_day.tasks:
            plan.days = [d for d in plan.days if d.day != from_day.day or d.tasks]
        target = _ensure_plan_day(plan, new_day_no)
        target.tasks.append(task)
    task.day = new_day_no
    task.date = new_date


def edit_task(
    repo: Repository,
    user_id: str,
    task_id: str,
    *,
    title: str | None = None,
    new_date: date | None = None,
    today: date | None = None,
) -> Task:
    if title is None and new_date is None:
        raise PlanEditError("En az bir alan (title veya date) gerekli.")
    today = today or date.today()
    plan = _active_plan(repo, user_id)
    plan_day, task = _find_task_in_plan(plan, task_id)
    _require_pending(task)

    if title is not None:
        cleaned = title.strip()
        if not cleaned:
            raise PlanEditError("Görev başlığı boş olamaz.")
        task.title = cleaned

    if new_date is not None:
        _reject_past(new_date, today=today)
        if task.date != new_date:
            _move_task(plan, task, plan_day, new_date)

    repo.save_plan(user_id, plan)
    return task


def add_task(
    repo: Repository,
    user_id: str,
    task_date: date,
    *,
    title: str,
    categories: list[Category] | None = None,
    tiny_version: str = "",
    duration_min: int = 15,
    today: date | None = None,
) -> Task:
    today = today or date.today()
    _reject_past(task_date, today=today)
    plan = _active_plan(repo, user_id)
    cleaned = title.strip()
    if not cleaned:
        raise PlanEditError("Görev başlığı boş olamaz.")

    cats = [
        c for c in (categories or ["İstikrar"])
        if c in CATEGORIES
    ]
    if not cats:
        raise PlanEditError("En az bir geçerli kategori gerekli.")

    day_no = _day_no_for_date(plan, task_date)
    if _count_tasks_on_day(plan, day_no) >= settings.MAX_TASKS_PER_DAY:
        raise PlanEditError("Bu gün için görev sınırına ulaşıldı.")

    plan_day = _ensure_plan_day(plan, day_no)
    if day_no > plan.batch_generated_until:
        plan.batch_generated_until = day_no
    task = Task(
        id=str(uuid.uuid4()),
        day=day_no,
        date=task_date,
        title=cleaned,
        categories=cats,
        tiny_version=tiny_version.strip() or "2 dakikalık en küçük adımla başla.",
        duration_min=duration_min,
        status="pending",
    )
    plan_day.tasks.append(task)
    repo.save_plan(user_id, plan)
    return task


def delete_task(
    repo: Repository,
    user_id: str,
    task_id: str,
) -> None:
    """Yalnız pending; puan/ceza yok."""
    plan = _active_plan(repo, user_id)
    plan_day, task = _find_task_in_plan(plan, task_id)
    _require_pending(task)
    plan_day.tasks = [t for t in plan_day.tasks if t.id != task_id]
    if not plan_day.tasks:
        plan.days = [d for d in plan.days if d.day != plan_day.day or d.tasks]
    repo.save_plan(user_id, plan)
    repo.delete_task(user_id, task_id)

"""FAZ 3 görev yaşam döngüsü: durum, puan ve point_log tek noktadan değişir."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.schemas import ProofRecord, ScoreEvent
from app.services import scoring_service
from app.storage.base import Repository

DAY_CLOSE_TIME = time(23, 59)
DEFAULT_TIMEZONE = ZoneInfo("Europe/Istanbul")


class TaskLifecycleError(ValueError):
    pass


class TaskNotFound(TaskLifecycleError):
    pass


class TaskAlreadyResolved(TaskLifecycleError):
    pass


def approve_proof(
    repository: Repository,
    user_id: str,
    proof: ProofRecord,
) -> list[ScoreEvent]:
    task = repository.get_task(user_id, proof.task_id)
    if task is None:
        raise TaskNotFound("Görev bulunamadı.")
    if task.status != "pending":
        raise TaskAlreadyResolved("Görev zaten sonuçlanmış.")

    state = repository.get_state(user_id)
    events = scoring_service.complete_task(state, task.categories)
    task.status = "done"
    task.proof_id = proof.id
    repository.save_state(state)
    repository.update_task(user_id, task)
    repository.append_point_log(user_id, task.id, events)
    return events


def excuse_task(
    repository: Repository, user_id: str, task_id: str
) -> list[ScoreEvent]:
    task = repository.get_task(user_id, task_id)
    if task is None:
        raise TaskNotFound("Görev bulunamadı.")
    if task.status != "pending":
        raise TaskAlreadyResolved("Görev zaten sonuçlanmış.")

    state = repository.get_state(user_id)
    events = scoring_service.miss_task_excused(state, task.categories)
    task.status = "missed_excused"
    repository.save_state(state)
    repository.update_task(user_id, task)
    repository.append_point_log(user_id, task.id, events)
    return events


def close_user_day(
    repository: Repository,
    user_id: str,
    day: date,
) -> dict:
    plan = repository.get_plan(user_id)
    if plan is None:
        return {"user_id": user_id, "day": day.isoformat(), "streak": "skipped",
                "penalized_tasks": 0}

    tasks = [
        task
        for plan_day in plan.days
        for task in plan_day.tasks
        if task.date == day
    ]
    if not tasks:
        return {"user_id": user_id, "day": day.isoformat(), "streak": "skipped",
                "penalized_tasks": 0}

    state = repository.get_state(user_id)
    if state.last_active_date == day:
        return {"user_id": user_id, "day": day.isoformat(), "streak": "noop",
                "penalized_tasks": 0}

    any_completed = any(task.status == "done" for task in tasks)
    penalized = 0
    for task in tasks:
        if task.status != "pending":
            continue
        events = scoring_service.miss_task_silent(state, task.categories)
        task.status = "missed_silent"
        repository.update_task(user_id, task)
        repository.append_point_log(user_id, task.id, events)
        penalized += 1

    streak_result = scoring_service.close_day(state, day, any_completed)
    repository.save_state(state)
    return {
        "user_id": user_id,
        "day": day.isoformat(),
        "streak": streak_result,
        "penalized_tasks": penalized,
        "streak_len": state.streak_len,
        "freeze_tokens": state.freeze_tokens,
    }


def latest_closed_day(now_utc: datetime, timezone_name: str) -> date:
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    try:
        user_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        user_timezone = DEFAULT_TIMEZONE
    local_now = now_utc.astimezone(user_timezone)
    if local_now.time().replace(tzinfo=None) >= DAY_CLOSE_TIME:
        return local_now.date()
    return local_now.date() - timedelta(days=1)


def close_due_users(repository: Repository, now_utc: datetime | None = None) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)
    results = [
        close_user_day(
            repository,
            cron_user.user_id,
            latest_closed_day(now_utc, cron_user.timezone),
        )
        for cron_user in repository.list_cron_users()
    ]
    return {
        "processed_users": len(results),
        "penalized_tasks": sum(row["penalized_tasks"] for row in results),
        "results": results,
    }

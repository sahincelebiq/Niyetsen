"""Timezone-aware FAZ 4 push scheduler, called by Railway cron."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services import bonus_service, push_service
from app.storage.base import Repository

log = logging.getLogger("niyetsen.notifications")
BONUS_LOCAL_HOUR = 15


def _local_now(now_utc: datetime, timezone_name: str) -> datetime:
    try:
        target = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        target = ZoneInfo("Europe/Istanbul")
    return now_utc.astimezone(target)


def _delivered(result: list[dict]) -> bool:
    return bool(result and result[0].get("status") == "ok")


def run_due_notifications(
    repository: Repository,
    now_utc: datetime | None = None,
) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)
    sent_task = 0
    sent_bonus = 0
    errors: list[str] = []
    for recipient in repository.list_notification_recipients():
        local = _local_now(now_utc, recipient.timezone)
        day = local.date()
        plan = repository.get_plan(recipient.user_id)
        pending_today = [
            task for plan_day in (plan.days if plan else [])
            for task in plan_day.tasks
            if task.date == day and task.status == "pending"
        ]
        if (
            pending_today
            and local.hour >= recipient.notif_hour
            and recipient.last_task_reminder_date != day
        ):
            try:
                result = push_service.send([push_service.PushMessage(
                    token=recipient.token,
                    title="Bugünün halkası seni bekliyor",
                    body=pending_today[0].title,
                    data={"url": "/daily", "taskId": pending_today[0].id},
                )])
                if _delivered(result):
                    repository.mark_task_reminder_sent(
                        recipient.user_id, recipient.token, day
                    )
                    sent_task += 1
            except Exception as exc:  # delivery failure must not stop other users
                log.warning("Görev push hatası (%s): %s", recipient.user_id, exc)
                errors.append(recipient.user_id)

        if (
            local.hour >= BONUS_LOCAL_HOUR
            and recipient.last_bonus_offer_date != day
        ):
            offer = bonus_service.offer_for_day(repository, recipient.user_id, day)
            try:
                result = push_service.send([push_service.PushMessage(
                    token=recipient.token,
                    title="10 puanlık küçük bir halka",
                    body=offer.title,
                    data={"url": "/bonus", "bonusId": offer.id},
                )])
                if _delivered(result):
                    repository.mark_bonus_offer_sent(
                        recipient.user_id, recipient.token, day
                    )
                    sent_bonus += 1
            except Exception as exc:
                log.warning("Bonus push hatası (%s): %s", recipient.user_id, exc)
                errors.append(recipient.user_id)

    return {
        "task_reminders_sent": sent_task,
        "bonus_offers_sent": sent_bonus,
        "delivery_errors": len(errors),
    }


def send_penalty_notifications(
    repository: Repository, close_results: list[dict]
) -> int:
    by_user = {
        row["user_id"]: row
        for row in close_results
        if row.get("penalized_tasks", 0) > 0
    }
    if not by_user:
        return 0
    sent = 0
    for recipient in repository.list_notification_recipients():
        row = by_user.get(recipient.user_id)
        if row is None:
            continue
        try:
            result = push_service.send([push_service.PushMessage(
                token=recipient.token,
                title="Zincirin için yeni bir fırsat",
                body=push_service.emotional_penalty_body(
                    int(row.get("streak_len", 0))
                ),
                data={"url": "/rank"},
            )])
            sent += int(_delivered(result))
        except Exception as exc:
            log.warning("Puan kaybı push hatası (%s): %s", recipient.user_id, exc)
    return sent

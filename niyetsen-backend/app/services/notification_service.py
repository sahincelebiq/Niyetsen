"""Timezone-aware FAZ 4 push scheduler, called by Railway cron."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services import bonus_service, project_service, push_service, recap_service
from app.storage.base import Repository

log = logging.getLogger("niyetsen.notifications")
BONUS_LOCAL_HOUR = 15


@dataclass(frozen=True)
class _PendingPush:
    message: push_service.PushMessage
    user_id: str
    kind: str
    on_success: Callable[[], None]


def _local_now(now_utc: datetime, timezone_name: str) -> datetime:
    try:
        target = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        target = ZoneInfo("Europe/Istanbul")
    return now_utc.astimezone(target)


def _local_minutes(local: datetime) -> int:
    return local.hour * 60 + local.minute


def _tarot_due_minute(notif_hour: int, notif_minute: int) -> int:
    """Görev bildiriminden 1 dk sonra — MASTER_PLAN §1.4 çift bildirim düzeni."""
    return notif_hour * 60 + notif_minute + 1


def _delivered(result: list[dict]) -> bool:
    return bool(result and result[0].get("status") == "ok")


def _flush_pending(pending: list[_PendingPush]) -> tuple[int, int, int, int, list[str]]:
    if not pending:
        return 0, 0, 0, 0, []
    sent_task = 0
    sent_bonus = 0
    sent_tarot = 0
    sent_recap = 0
    errors: list[str] = []
    try:
        results = push_service.send_batched([item.message for item in pending])
    except Exception as exc:
        log.warning("Push batch hatası (%d mesaj): %s", len(pending), exc)
        return 0, 0, 0, 0, [item.user_id for item in pending]
    for item, result in zip(pending, results, strict=False):
        if _delivered([result]):
            item.on_success()
            if item.kind == "task":
                sent_task += 1
            elif item.kind == "bonus":
                sent_bonus += 1
            elif item.kind == "tarot":
                sent_tarot += 1
            elif item.kind == "recap":
                sent_recap += 1
        else:
            errors.append(item.user_id)
    return sent_task, sent_bonus, sent_tarot, sent_recap, errors


def run_due_notifications(
    repository: Repository,
    now_utc: datetime | None = None,
) -> dict:
    now_utc = now_utc or datetime.now(timezone.utc)
    pending: list[_PendingPush] = []
    for recipient in repository.list_notification_recipients():
        try:
            local = _local_now(now_utc, recipient.timezone)
            day = local.date()
            local_min = _local_minutes(local)
            notif_min = recipient.notif_hour * 60 + recipient.notif_minute
            pending_today = [
                item.task
                for item in project_service.get_today_tasks(
                    repository, recipient.user_id, today=day
                )
                if item.task.status == "pending"
            ]
            if (
                pending_today
                and local_min >= notif_min
                and recipient.last_task_reminder_date != day
            ):
                pending.append(_PendingPush(
                    message=push_service.PushMessage(
                        token=recipient.token,
                        title="Bugünün halkası seni bekliyor",
                        body=pending_today[0].title,
                        data={"url": "/daily", "taskId": pending_today[0].id},
                    ),
                    user_id=recipient.user_id,
                    kind="task",
                    on_success=lambda r=recipient, d=day: (
                        repository.mark_task_reminder_sent(r.user_id, r.token, d)
                    ),
                ))

            if (
                local_min >= _tarot_due_minute(
                    recipient.notif_hour, recipient.notif_minute
                )
                and recipient.last_tarot_push_date != day
            ):
                pending.append(_PendingPush(
                    message=push_service.PushMessage(
                        token=recipient.token,
                        title="Bugünün kartı seni bekliyor",
                        body=(
                            "Günlük tarot çekiminde niyetinin yönüne "
                            "küçük bir ipucu var."
                        ),
                        data={"url": "/tarot"},
                    ),
                    user_id=recipient.user_id,
                    kind="tarot",
                    on_success=lambda r=recipient, d=day: (
                        repository.mark_tarot_push_sent(r.user_id, r.token, d)
                    ),
                ))

            if (
                local.hour >= BONUS_LOCAL_HOUR
                and recipient.last_bonus_offer_date != day
            ):
                offer = bonus_service.offer_for_day(
                    repository, recipient.user_id, day
                )
                pending.append(_PendingPush(
                    message=push_service.PushMessage(
                        token=recipient.token,
                        title="10 puanlık küçük bir halka",
                        body=offer.title,
                        data={"url": "/bonus", "bonusId": offer.id},
                    ),
                    user_id=recipient.user_id,
                    kind="bonus",
                    on_success=lambda r=recipient, d=day: (
                        repository.mark_bonus_offer_sent(r.user_id, r.token, d)
                    ),
                ))

            # FAZ 8.8 — Niyetsen Raporu: 14. gün + her 30 günde bir.
            plan = repository.get_plan(recipient.user_id)
            days_in = (day - plan.start_date).days + 1 if plan else 0
            if (
                local_min >= notif_min
                and recipient.last_recap_push_date != day
                and recap_service.is_recap_push_due(days_in)
            ):
                period_days = recap_service.recap_push_period_days(days_in)
                pending.append(_PendingPush(
                    message=push_service.PushMessage(
                        token=recipient.token,
                        title="Raporun hazır ✨",
                        body=recap_service.recap_push_body(period_days),
                        data={"screen": "rapor", "url": "/rapor"},
                    ),
                    user_id=recipient.user_id,
                    kind="recap",
                    on_success=lambda r=recipient, d=day: (
                        repository.mark_recap_push_sent(r.user_id, r.token, d)
                    ),
                ))
        except Exception:
            log.exception(
                "Bildirim işlenemedi (user_id=%s)", recipient.user_id
            )

    sent_task, sent_bonus, sent_tarot, sent_recap, errors = _flush_pending(pending)
    return {
        "task_reminders_sent": sent_task,
        "tarot_pushes_sent": sent_tarot,
        "bonus_offers_sent": sent_bonus,
        "recap_pushes_sent": sent_recap,
        "delivery_errors": len(set(errors)),
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
    pending: list[_PendingPush] = []
    for recipient in repository.list_notification_recipients():
        row = by_user.get(recipient.user_id)
        if row is None:
            continue
        pending.append(_PendingPush(
            message=push_service.PushMessage(
                token=recipient.token,
                title="Zincirin için yeni bir fırsat",
                body=push_service.emotional_penalty_body(
                    int(row.get("streak_len", 0))
                ),
                data={"url": "/rank"},
            ),
            user_id=recipient.user_id,
            kind="penalty",
            on_success=lambda: None,
        ))
    sent_task, _, _, _, _ = _flush_pending(pending)
    return sent_task

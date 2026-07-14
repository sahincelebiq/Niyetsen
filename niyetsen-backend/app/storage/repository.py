"""
Niyetsen — Depolama Katmanı
MVP: bellek-içi (uygulama yeniden başlayınca sıfırlanır — bilinçli, MVP kuralı).
v1: Cursor, SupabaseRepository'yi AYNI arayüzle yazar; routes hiç değişmez.
Tablolar MASTER_PLAN §2'de tanımlı — şema uydurulmaz.
Cursor notu: Repository ABC'si app/storage/base.py'de yaşar (bu dosyayla
supabase_repository.py arasında dairesel import'u önlemek için).
"""
from __future__ import annotations

import time
import uuid
from datetime import date as dt_date, datetime, timezone
from threading import RLock
from typing import Optional

from app.config import BONUS_POINTS, settings
from app.models.schemas import (
    BonusOffer, ChatMessage, CollectedIntent, ConsentRecord, CronUser, DailyTaskItem,
    GameState, NotificationRecipient, Plan, PlanSummary, PointLogRecord, ProofAttemptClaim,
    ProofRecord, ProofResult, PushTokenRecord, ScoreEvent, Task, UserProfile,
)
from app.storage.base import Repository


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._plans_by_user: dict[str, dict[str, Plan]] = {}
        self._plan_meta: dict[str, dict[str, dict]] = {}
        self._active_plan_id: dict[str, str] = {}
        self._attempts: dict[tuple[str, str], int] = {}
        self._chat_history: dict[tuple[str, str], list[ChatMessage]] = {}
        self._intents: dict[tuple[str, str], list[dict]] = {}
        self._profiles: dict[str, UserProfile] = {}
        self._proof_photos: dict[str, bytes] = {}
        self._proofs: dict[str, list[ProofRecord]] = {}
        self._point_log: dict[str, list[PointLogRecord]] = {}
        self._proof_requests: dict[
            tuple[str, str, str], tuple[str, int, ProofResult | None]
        ] = {}
        self._proof_request_started: dict[tuple[str, str, str], float] = {}
        self._proof_locks: dict[tuple[str, str], RLock] = {}
        self._consents: dict[str, dict[tuple[str, str], ConsentRecord]] = {}
        self._push_tokens: dict[str, PushTokenRecord] = {}
        self._bonus_offers: dict[str, BonusOffer] = {}
        self._subscriptions: dict[str, dict] = {}

    def get_state(self, user_id: str) -> GameState:
        if user_id not in self._states:
            self._states[user_id] = GameState(user_id=user_id)
        return self._states[user_id]

    def save_state(self, state: GameState) -> None:
        self._states[state.user_id] = state

    def _user_plans(self, user_id: str) -> dict[str, Plan]:
        return self._plans_by_user.setdefault(user_id, {})

    def _user_meta(self, user_id: str) -> dict[str, dict]:
        return self._plan_meta.setdefault(user_id, {})

    def _ensure_active_plan_id(self, user_id: str) -> str:
        active = self._active_plan_id.get(user_id)
        if active and active in self._user_plans(user_id):
            return active
        plans = self._user_plans(user_id)
        if plans:
            first_id = sorted(
                plans,
                key=lambda plan_id: self._user_meta(user_id).get(plan_id, {}).get("slot_no", 1),
            )[0]
            self._active_plan_id[user_id] = first_id
            return first_id
        return self.create_draft_plan(user_id, name="Plan 1", slot_no=1)

    def _plan_from_store(self, user_id: str, plan_id: str) -> Optional[Plan]:
        plan = self._user_plans(user_id).get(plan_id)
        if not plan:
            return None
        meta = self._user_meta(user_id).get(plan_id, {})
        return plan.model_copy(
            update={
                "name": meta.get("name", "Planım"),
                "slot_no": meta.get("slot_no", 1),
                "is_active": self._active_plan_id.get(user_id) == plan_id,
            }
        )

    def save_plan(self, user_id: str, plan: Plan) -> None:
        plan_id = plan.id
        self._user_plans(user_id)[plan_id] = plan.model_copy(
            update={"name": plan.name, "slot_no": plan.slot_no}
        )
        meta = self._user_meta(user_id).setdefault(
            plan_id,
            {"name": plan.name or "Planım", "slot_no": plan.slot_no or 1},
        )
        meta["name"] = plan.name or meta["name"]
        meta["slot_no"] = plan.slot_no or meta["slot_no"]
        self._active_plan_id[user_id] = plan_id

    def get_plan(self, user_id: str) -> Optional[Plan]:
        plan_id = self._active_plan_id.get(user_id)
        if not plan_id:
            plans = self._user_plans(user_id)
            if not plans:
                return None
            plan_id = self._ensure_active_plan_id(user_id)
        plan = self._plan_from_store(user_id, plan_id)
        if plan and not plan.days:
            return None
        return plan

    def get_plan_by_id(self, user_id: str, plan_id: str) -> Optional[Plan]:
        plan = self._plan_from_store(user_id, plan_id)
        if not plan or not plan.days:
            return None
        return plan

    def list_plan_summaries(self, user_id: str) -> list[PlanSummary]:
        self._ensure_active_plan_id(user_id)
        active_id = self._active_plan_id.get(user_id)
        summaries: list[PlanSummary] = []
        for plan_id, plan in self._user_plans(user_id).items():
            meta = self._user_meta(user_id).get(plan_id, {})
            summaries.append(
                PlanSummary(
                    id=plan_id,
                    name=meta.get("name", "Planım"),
                    slot_no=meta.get("slot_no", 1),
                    is_active=plan_id == active_id,
                    has_content=bool(plan.days),
                )
            )
        return sorted(summaries, key=lambda item: item.slot_no)

    def set_active_plan(self, user_id: str, plan_id: str) -> None:
        if plan_id not in self._user_plans(user_id):
            raise ValueError("Plan bulunamadı.")
        self._active_plan_id[user_id] = plan_id

    def create_draft_plan(self, user_id: str, *, name: str, slot_no: int) -> str:
        plan_id = str(uuid.uuid4())
        draft = Plan(
            id=plan_id,
            duration_days=365,
            batch_generated_until=0,
            start_date=dt_date.today(),
            days=[],
            name=name,
            slot_no=slot_no,
        )
        self._user_plans(user_id)[plan_id] = draft
        self._user_meta(user_id)[plan_id] = {"name": name, "slot_no": slot_no}
        self._active_plan_id[user_id] = plan_id
        return plan_id

    def rename_plan(self, user_id: str, plan_id: str, name: str) -> None:
        if plan_id not in self._user_plans(user_id):
            raise ValueError("Plan bulunamadı.")
        self._user_meta(user_id).setdefault(plan_id, {})["name"] = name
        plan = self._user_plans(user_id)[plan_id]
        self._user_plans(user_id)[plan_id] = plan.model_copy(update={"name": name})

    def plan_belongs_to_user(self, user_id: str, plan_id: str) -> bool:
        return plan_id in self._user_plans(user_id)

    def count_completed_plans(self, user_id: str) -> int:
        return sum(1 for plan in self._user_plans(user_id).values() if plan.days)

    def next_plan_slot(self, user_id: str) -> int:
        slots = [
            meta.get("slot_no", 1)
            for meta in self._user_meta(user_id).values()
        ]
        return (max(slots) if slots else 0) + 1

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        for plan in self._user_plans(user_id).values():
            for day in plan.days:
                for task in day.tasks:
                    if task.id == task_id:
                        return task
        return None

    def list_tasks_for_date(self, user_id: str, day: dt_date) -> list[Task]:
        tasks: list[Task] = []
        for plan in self._user_plans(user_id).values():
            for plan_day in plan.days:
                for task in plan_day.tasks:
                    if task.date == day:
                        tasks.append(task)
        return tasks

    def list_daily_tasks_for_date(
        self, user_id: str, day: dt_date
    ) -> list[DailyTaskItem]:
        items: list[DailyTaskItem] = []
        for plan_id, plan in self._user_plans(user_id).items():
            meta = self._user_meta(user_id).get(plan_id, {})
            for plan_day in plan.days:
                for task in plan_day.tasks:
                    if task.date == day:
                        items.append(DailyTaskItem(
                            plan_id=plan_id,
                            plan_name=meta.get("name", plan.name),
                            task=task,
                        ))
        return items

    def update_task(self, user_id: str, task: Task) -> None:
        for plan in self._user_plans(user_id).values():
            for day in plan.days:
                for index, existing in enumerate(day.tasks):
                    if existing.id == task.id:
                        day.tasks[index] = task
                        return

    def get_proof_attempts(self, user_id: str, task_id: str) -> int:
        if self.get_task(user_id, task_id) is None:
            return 0
        return self._attempts.get((user_id, task_id), 0)

    def incr_proof_attempts(self, user_id: str, task_id: str) -> int:
        if self.get_task(user_id, task_id) is None:
            return 0
        key = (user_id, task_id)
        self._attempts[key] = self._attempts.get(key, 0) + 1
        return self._attempts[key]

    def _reclaim_stale_proof_requests(self, user_id: str, task_id: str) -> None:
        now = time.monotonic()
        stale_keys = [
            key
            for key, started in self._proof_request_started.items()
            if key[0] == user_id
            and key[1] == task_id
            and now - started > 120
            and self._proof_requests.get(key, ("", 0, None))[0] == "in_progress"
        ]
        for key in stale_keys:
            self._proof_requests.pop(key, None)
            self._proof_request_started.pop(key, None)

    def begin_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> ProofAttemptClaim:
        lock = self._proof_locks.setdefault((user_id, task_id), RLock())
        with lock:
            self._reclaim_stale_proof_requests(user_id, task_id)
            task = self.get_task(user_id, task_id)
            if task is None:
                raise ValueError("Görev bulunamadı.")
            request_key = (user_id, task_id, idempotency_key)
            existing = self._proof_requests.get(request_key)
            if existing:
                status, attempt_no, result = existing
                if status == "completed":
                    return ProofAttemptClaim(
                        status=status, attempt_no=attempt_no, result=result
                    )
                if status == "in_progress":
                    return ProofAttemptClaim(
                        status="in_progress",
                        attempt_no=attempt_no,
                        result=result,
                    )
            if task.status != "pending":
                raise RuntimeError("Görev zaten sonuçlanmış.")
            if any(
                key[:2] == (user_id, task_id) and value[0] == "in_progress"
                for key, value in self._proof_requests.items()
            ):
                return ProofAttemptClaim(
                    status="in_progress",
                    attempt_no=self._attempts.get((user_id, task_id), 0) + 1,
                )
            attempt_no = self._attempts.get((user_id, task_id), 0) + 1
            self._proof_requests[request_key] = ("in_progress", attempt_no, None)
            self._proof_request_started[request_key] = time.monotonic()
            return ProofAttemptClaim(status="started", attempt_no=attempt_no)

    def finish_proof_attempt(
        self,
        user_id: str,
        task_id: str,
        idempotency_key: str,
        result: ProofResult,
    ) -> None:
        lock = self._proof_locks.setdefault((user_id, task_id), RLock())
        with lock:
            request_key = (user_id, task_id, idempotency_key)
            existing = self._proof_requests.get(request_key)
            if not existing or existing[0] != "in_progress":
                raise RuntimeError("Kanıt isteği etkin değil.")
            attempt_no = existing[1]
            self._attempts[(user_id, task_id)] = attempt_no
            self._proof_requests[request_key] = (
                "completed", attempt_no, result.model_copy(deep=True)
            )

    def abort_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> None:
        lock = self._proof_locks.setdefault((user_id, task_id), RLock())
        with lock:
            request_key = (user_id, task_id, idempotency_key)
            if self._proof_requests.get(request_key, ("", 0, None))[0] == "in_progress":
                self._proof_requests.pop(request_key, None)
                self._proof_request_started.pop(request_key, None)

    def store_proof_photo(
        self, user_id: str, task_id: str, image_bytes: bytes, mime_type: str
    ) -> str:
        if self.get_task(user_id, task_id) is None:
            raise ValueError("Görev kullanıcıya ait değil.")
        extension = "jpg" if mime_type == "image/jpeg" else "png"
        path = f"{user_id}/{uuid.uuid4()}.{extension}"
        self._proof_photos[path] = image_bytes
        return f"storage://proofs/{path}"

    def save_proof(self, user_id: str, proof: ProofRecord) -> None:
        if self.get_task(user_id, proof.task_id) is None:
            raise ValueError("Görev kullanıcıya ait değil.")
        self._proofs.setdefault(user_id, []).append(proof)

    def get_proofs(self, user_id: str, task_id: str) -> list[ProofRecord]:
        if self.get_task(user_id, task_id) is None:
            return []
        return [
            proof for proof in self._proofs.get(user_id, [])
            if proof.task_id == task_id
        ]

    def append_point_log(
        self, user_id: str, task_id: str | None, events: list[ScoreEvent]
    ) -> None:
        rows = self._point_log.setdefault(user_id, [])
        rows.extend(
            PointLogRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                task_id=task_id,
                category=event.category,
                delta=event.delta,
                reason=event.reason,
            )
            for event in events
        )

    def get_point_log(self, user_id: str) -> list[PointLogRecord]:
        return list(self._point_log.get(user_id, []))

    def list_cron_users(self) -> list[CronUser]:
        user_ids = (
            set(self._profiles)
            | set(self._plans_by_user)
            | set(self._states)
            | {user_id for user_id, _ in self._chat_history}
        )
        return [
            CronUser(
                user_id=user_id,
                timezone=self._profiles.get(user_id, UserProfile()).timezone,
            )
            for user_id in sorted(user_ids)
        ]

    def append_chat_message(self, user_id: str, message: ChatMessage) -> None:
        plan_id = self._ensure_active_plan_id(user_id)
        history = self._chat_history.setdefault((user_id, plan_id), [])
        if message.id and any(existing.id == message.id for existing in history):
            return
        history.append(message)

    def get_chat_history(self, user_id: str) -> list[ChatMessage]:
        plan_id = self._ensure_active_plan_id(user_id)
        return list(self._chat_history.get((user_id, plan_id), []))

    def save_intent(
        self,
        user_id: str,
        collected: CollectedIntent,
        duration_days: int,
        ready_for_plan: bool = False,
    ) -> None:
        plan_id = self._ensure_active_plan_id(user_id)
        active = {
            "collected": collected.model_dump(),
            "duration_days": duration_days,
            "ready_for_plan": ready_for_plan,
            "status": "active",
        }
        intents = self._intents.setdefault((user_id, plan_id), [])
        for index, intent in enumerate(intents):
            if intent["status"] == "active":
                intents[index] = active
                return
        intents.append(active)

    def get_active_intent(self, user_id: str) -> tuple[CollectedIntent, bool] | None:
        plan_id = self._ensure_active_plan_id(user_id)
        for intent in reversed(self._intents.get((user_id, plan_id), [])):
            if intent["status"] == "active":
                return CollectedIntent(**intent["collected"]), bool(intent["ready_for_plan"])
        return None

    def complete_active_intent(self, user_id: str) -> None:
        plan_id = self._active_plan_id.get(user_id)
        if not plan_id:
            return
        for intent in reversed(self._intents.get((user_id, plan_id), [])):
            if intent["status"] == "active":
                intent["status"] = "done"
                return

    def get_profile(self, user_id: str) -> UserProfile:
        return self._profiles.get(user_id, UserProfile())

    def save_profile(self, user_id: str, profile: UserProfile) -> None:
        self._profiles[user_id] = profile

    def get_consents(self, user_id: str) -> list[ConsentRecord]:
        return [
            record.model_copy(deep=True)
            for record in self._consents.get(user_id, {}).values()
        ]

    def save_consent(self, user_id: str, consent: ConsentRecord) -> None:
        self._consents.setdefault(user_id, {})[
            (consent.kind, consent.version)
        ] = consent.model_copy(deep=True)

    def upsert_push_token(self, token: PushTokenRecord) -> None:
        self._push_tokens[token.token] = token.model_copy(deep=True)

    def disable_push_token(self, user_id: str, token: str) -> None:
        existing = self._push_tokens.get(token)
        if existing and existing.user_id == user_id:
            existing.enabled = False

    def list_notification_recipients(self) -> list[NotificationRecipient]:
        recipients: list[NotificationRecipient] = []
        for token in self._push_tokens.values():
            if not token.enabled:
                continue
            profile = self._profiles.get(token.user_id, UserProfile())
            recipients.append(NotificationRecipient(
                user_id=token.user_id,
                timezone=profile.timezone,
                notif_hour=profile.notif_hour,
                notif_minute=profile.notif_minute,
                token=token.token,
                last_task_reminder_date=token.last_task_reminder_date,
                last_bonus_offer_date=token.last_bonus_offer_date,
            ))
        return recipients

    def mark_task_reminder_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        existing = self._push_tokens.get(token)
        if existing and existing.user_id == user_id:
            existing.last_task_reminder_date = day

    def mark_bonus_offer_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        existing = self._push_tokens.get(token)
        if existing and existing.user_id == user_id:
            existing.last_bonus_offer_date = day

    def get_bonus_for_day(self, user_id: str, day: dt_date) -> BonusOffer | None:
        return next((
            offer.model_copy(deep=True)
            for offer in self._bonus_offers.values()
            if offer.user_id == user_id and offer.day == day
        ), None)

    def get_active_bonus(self, user_id: str) -> BonusOffer | None:
        offers = [
            offer for offer in self._bonus_offers.values()
            if offer.user_id == user_id and offer.status == "offered"
        ]
        if not offers:
            return None
        return max(offers, key=lambda offer: offer.offered_at).model_copy(deep=True)

    def save_bonus_offer(self, offer: BonusOffer) -> BonusOffer:
        existing = self.get_bonus_for_day(offer.user_id, offer.day)
        if existing:
            return existing
        self._bonus_offers[offer.id] = offer.model_copy(deep=True)
        return offer.model_copy(deep=True)

    def claim_bonus_completion(
        self, user_id: str, offer_id: str, completion_id: str
    ) -> bool:
        offer = self._bonus_offers.get(offer_id)
        if (
            offer is None or offer.user_id != user_id
            or offer.status != "offered"
            or any(
                other.user_id == user_id
                and other.completion_id == completion_id
                for other in self._bonus_offers.values()
            )
        ):
            return False
        offer.status = "completed"
        offer.completion_id = completion_id
        offer.completed_at = datetime.now(timezone.utc)
        state = self.get_state(user_id)
        state.points[offer.category] += BONUS_POINTS
        self.append_point_log(
            user_id,
            None,
            [ScoreEvent(
                category=offer.category,
                delta=BONUS_POINTS,
                reason=f"motivasyon bonus görevi:{offer.id}",
            )],
        )
        return True

    def delete_account(self, user_id: str) -> None:
        self._states.pop(user_id, None)
        self._plans_by_user.pop(user_id, None)
        self._plan_meta.pop(user_id, None)
        self._active_plan_id.pop(user_id, None)
        self._chat_history = {
            key: value for key, value in self._chat_history.items() if key[0] != user_id
        }
        self._intents = {
            key: value for key, value in self._intents.items() if key[0] != user_id
        }
        self._profiles.pop(user_id, None)
        self._proofs.pop(user_id, None)
        self._point_log.pop(user_id, None)
        self._consents.pop(user_id, None)
        self._push_tokens = {
            token: row for token, row in self._push_tokens.items()
            if row.user_id != user_id
        }
        self._bonus_offers = {
            offer_id: offer for offer_id, offer in self._bonus_offers.items()
            if offer.user_id != user_id
        }
        self._proof_requests = {
            key: value for key, value in self._proof_requests.items()
            if key[0] != user_id
        }
        self._proof_photos = {
            path: value
            for path, value in self._proof_photos.items()
            if not path.startswith(f"{user_id}/")
        }
        self._attempts = {
            key: value for key, value in self._attempts.items() if key[0] != user_id
        }
        self._subscriptions.pop(user_id, None)

    def get_subscription_row(self, user_id: str) -> dict:
        profile = self._profiles.get(user_id, UserProfile())
        row = self._subscriptions.setdefault(
            user_id,
            {
                "subscription_status": "free",
                "trial_started_at": None,
                "timezone": profile.timezone,
            },
        )
        row["timezone"] = profile.timezone
        return row

    def update_subscription(
        self,
        user_id: str,
        *,
        subscription_status: str | None = None,
        trial_started_at: datetime | None = None,
    ) -> None:
        row = self.get_subscription_row(user_id)
        if subscription_status is not None:
            row["subscription_status"] = subscription_status
        if trial_started_at is not None:
            row["trial_started_at"] = trial_started_at


def _build_repo() -> Repository:
    if settings.USE_SUPABASE_DB:
        # Geç import: supabase paketi sadece bu yol seçildiğinde gerekli olsun.
        from app.storage.supabase_repository import SupabaseRepository
        return SupabaseRepository()
    return InMemoryRepository()


# Uygulama genelinde tek örnek. USE_SUPABASE_DB=false (varsayılan, testler dahil)
# iken bellek-içi; true iken gerçek Supabase kalıcılığı.
repo: Repository = _build_repo()

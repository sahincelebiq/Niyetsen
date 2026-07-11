"""
Niyetsen — Depolama Katmanı
MVP: bellek-içi (uygulama yeniden başlayınca sıfırlanır — bilinçli, MVP kuralı).
v1: Cursor, SupabaseRepository'yi AYNI arayüzle yazar; routes hiç değişmez.
Tablolar MASTER_PLAN §2'de tanımlı — şema uydurulmaz.
Cursor notu: Repository ABC'si app/storage/base.py'de yaşar (bu dosyayla
supabase_repository.py arasında dairesel import'u önlemek için).
"""
from __future__ import annotations

import uuid
from datetime import date as dt_date, datetime, timezone
from threading import RLock
from typing import Optional

from app.config import BONUS_POINTS, settings
from app.models.schemas import (
    BonusOffer, ChatMessage, CollectedIntent, ConsentRecord, CronUser, GameState,
    NotificationRecipient, Plan, PointLogRecord, ProofAttemptClaim, ProofRecord,
    ProofResult, PushTokenRecord, ScoreEvent, Task, UserProfile,
)
from app.storage.base import Repository


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._states: dict[str, GameState] = {}
        self._plans: dict[str, Plan] = {}
        self._attempts: dict[tuple[str, str], int] = {}
        self._chat_history: dict[str, list[ChatMessage]] = {}
        self._intents: dict[str, list[dict]] = {}
        self._profiles: dict[str, UserProfile] = {}
        self._proof_photos: dict[str, bytes] = {}
        self._proofs: dict[str, list[ProofRecord]] = {}
        self._point_log: dict[str, list[PointLogRecord]] = {}
        self._proof_requests: dict[
            tuple[str, str, str], tuple[str, int, ProofResult | None]
        ] = {}
        self._proof_locks: dict[tuple[str, str], RLock] = {}
        self._consents: dict[str, dict[tuple[str, str], ConsentRecord]] = {}
        self._push_tokens: dict[str, PushTokenRecord] = {}
        self._bonus_offers: dict[str, BonusOffer] = {}

    def get_state(self, user_id: str) -> GameState:
        if user_id not in self._states:
            self._states[user_id] = GameState(user_id=user_id)
        return self._states[user_id]

    def save_state(self, state: GameState) -> None:
        self._states[state.user_id] = state

    def save_plan(self, user_id: str, plan: Plan) -> None:
        self._plans[user_id] = plan

    def get_plan(self, user_id: str) -> Optional[Plan]:
        return self._plans.get(user_id)

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        plan = self._plans.get(user_id)
        if not plan:
            return None
        for day in plan.days:
            for t in day.tasks:
                if t.id == task_id:
                    return t
        return None

    def update_task(self, user_id: str, task: Task) -> None:
        plan = self._plans.get(user_id)
        if not plan:
            return
        for day in plan.days:
            for i, t in enumerate(day.tasks):
                if t.id == task.id:
                    day.tasks[i] = task
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

    def begin_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> ProofAttemptClaim:
        lock = self._proof_locks.setdefault((user_id, task_id), RLock())
        with lock:
            task = self.get_task(user_id, task_id)
            if task is None:
                raise ValueError("Görev bulunamadı.")
            request_key = (user_id, task_id, idempotency_key)
            existing = self._proof_requests.get(request_key)
            if existing:
                status, attempt_no, result = existing
                return ProofAttemptClaim(
                    status=status, attempt_no=attempt_no, result=result
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
            | set(self._plans)
            | set(self._states)
            | set(self._chat_history)
        )
        return [
            CronUser(
                user_id=user_id,
                timezone=self._profiles.get(user_id, UserProfile()).timezone,
            )
            for user_id in sorted(user_ids)
        ]

    def append_chat_message(self, user_id: str, message: ChatMessage) -> None:
        history = self._chat_history.setdefault(user_id, [])
        if message.id and any(existing.id == message.id for existing in history):
            return
        history.append(message)

    def get_chat_history(self, user_id: str) -> list[ChatMessage]:
        return list(self._chat_history.get(user_id, []))

    def save_intent(
        self,
        user_id: str,
        collected: CollectedIntent,
        duration_days: int,
        ready_for_plan: bool = False,
    ) -> None:
        active = {
            "collected": collected.model_dump(),
            "duration_days": duration_days,
            "ready_for_plan": ready_for_plan,
            "status": "active",
        }
        intents = self._intents.setdefault(user_id, [])
        for index, intent in enumerate(intents):
            if intent["status"] == "active":
                intents[index] = active
                return
        intents.append(active)

    def get_active_intent(self, user_id: str) -> tuple[CollectedIntent, bool] | None:
        for intent in reversed(self._intents.get(user_id, [])):
            if intent["status"] == "active":
                return CollectedIntent(**intent["collected"]), bool(intent["ready_for_plan"])
        return None

    def complete_active_intent(self, user_id: str) -> None:
        for intent in reversed(self._intents.get(user_id, [])):
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
        self._plans.pop(user_id, None)
        self._chat_history.pop(user_id, None)
        self._intents.pop(user_id, None)
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


def _build_repo() -> Repository:
    if settings.USE_SUPABASE_DB:
        # Geç import: supabase paketi sadece bu yol seçildiğinde gerekli olsun.
        from app.storage.supabase_repository import SupabaseRepository
        return SupabaseRepository()
    return InMemoryRepository()


# Uygulama genelinde tek örnek. USE_SUPABASE_DB=false (varsayılan, testler dahil)
# iken bellek-içi; true iken gerçek Supabase kalıcılığı.
repo: Repository = _build_repo()

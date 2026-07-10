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
from typing import Optional

from app.config import settings
from app.models.schemas import (
    ChatMessage, CollectedIntent, CronUser, GameState, Plan, PointLogRecord,
    ProofRecord, ScoreEvent, Task, UserProfile,
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

    def delete_account(self, user_id: str) -> None:
        self._states.pop(user_id, None)
        self._plans.pop(user_id, None)
        self._chat_history.pop(user_id, None)
        self._intents.pop(user_id, None)
        self._profiles.pop(user_id, None)
        self._proofs.pop(user_id, None)
        self._point_log.pop(user_id, None)
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

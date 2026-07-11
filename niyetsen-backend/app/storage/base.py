"""
Niyetsen — Depolama arayüzü (soyut sözleşme).
Ayrı dosyada: hem repository.py (InMemory + repo seçici) hem de
supabase_repository.py bunu import eder; repository.py çalışma zamanında
supabase_repository'yi GEÇ import ettiği için (USE_SUPABASE_DB=true iken)
Repository'nin burada, iki yönlü bağımlılık yaratmayan bir yerde durması gerekir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date as dt_date
from typing import Optional

from app.models.schemas import (
    BonusOffer, ChatMessage, CollectedIntent, ConsentRecord, CronUser, GameState,
    NotificationRecipient, Plan, PointLogRecord, ProofAttemptClaim, ProofRecord,
    ProofResult, PushTokenRecord, ScoreEvent, Task, UserProfile,
)


class Repository(ABC):
    """Tek gerçek arayüz. Yeni backend eklemek = bu sınıfı implemente etmek."""

    @abstractmethod
    def get_state(self, user_id: str) -> GameState: ...

    @abstractmethod
    def save_state(self, state: GameState) -> None: ...

    @abstractmethod
    def save_plan(self, user_id: str, plan: Plan) -> None: ...

    @abstractmethod
    def get_plan(self, user_id: str) -> Optional[Plan]: ...

    @abstractmethod
    def get_task(self, user_id: str, task_id: str) -> Optional[Task]: ...

    @abstractmethod
    def update_task(self, user_id: str, task: Task) -> None: ...

    @abstractmethod
    def get_proof_attempts(self, user_id: str, task_id: str) -> int: ...

    @abstractmethod
    def incr_proof_attempts(self, user_id: str, task_id: str) -> int: ...

    @abstractmethod
    def begin_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> ProofAttemptClaim: ...

    @abstractmethod
    def finish_proof_attempt(
        self,
        user_id: str,
        task_id: str,
        idempotency_key: str,
        result: ProofResult,
    ) -> None: ...

    @abstractmethod
    def abort_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> None: ...

    @abstractmethod
    def store_proof_photo(
        self, user_id: str, task_id: str, image_bytes: bytes, mime_type: str
    ) -> str: ...

    @abstractmethod
    def save_proof(self, user_id: str, proof: ProofRecord) -> None: ...

    @abstractmethod
    def get_proofs(self, user_id: str, task_id: str) -> list[ProofRecord]: ...

    @abstractmethod
    def append_point_log(
        self, user_id: str, task_id: str | None, events: list[ScoreEvent]
    ) -> None: ...

    @abstractmethod
    def get_point_log(self, user_id: str) -> list[PointLogRecord]: ...

    @abstractmethod
    def list_cron_users(self) -> list[CronUser]: ...

    # --- Sohbet geçmişi + niyet kalıcılığı (Faz 2) ---
    @abstractmethod
    def append_chat_message(self, user_id: str, message: ChatMessage) -> None: ...

    @abstractmethod
    def get_chat_history(self, user_id: str) -> list[ChatMessage]: ...

    @abstractmethod
    def save_intent(
        self,
        user_id: str,
        collected: CollectedIntent,
        duration_days: int,
        ready_for_plan: bool = False,
    ) -> None: ...

    @abstractmethod
    def get_active_intent(self, user_id: str) -> tuple[CollectedIntent, bool] | None: ...

    @abstractmethod
    def complete_active_intent(self, user_id: str) -> None: ...

    @abstractmethod
    def get_profile(self, user_id: str) -> UserProfile: ...

    @abstractmethod
    def save_profile(self, user_id: str, profile: UserProfile) -> None: ...

    @abstractmethod
    def get_consents(self, user_id: str) -> list[ConsentRecord]: ...

    @abstractmethod
    def save_consent(self, user_id: str, consent: ConsentRecord) -> None: ...

    @abstractmethod
    def upsert_push_token(self, token: PushTokenRecord) -> None: ...

    @abstractmethod
    def disable_push_token(self, user_id: str, token: str) -> None: ...

    @abstractmethod
    def list_notification_recipients(self) -> list[NotificationRecipient]: ...

    @abstractmethod
    def mark_task_reminder_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None: ...

    @abstractmethod
    def mark_bonus_offer_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None: ...

    @abstractmethod
    def get_bonus_for_day(self, user_id: str, day: dt_date) -> BonusOffer | None: ...

    @abstractmethod
    def get_active_bonus(self, user_id: str) -> BonusOffer | None: ...

    @abstractmethod
    def save_bonus_offer(self, offer: BonusOffer) -> BonusOffer: ...

    @abstractmethod
    def claim_bonus_completion(
        self, user_id: str, offer_id: str, completion_id: str
    ) -> bool: ...

    @abstractmethod
    def delete_account(self, user_id: str) -> None: ...

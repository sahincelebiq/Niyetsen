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
    BonusOffer, ChatMessage, ChatThread, CollectedIntent, ConsentRecord, CronUser,
    DailyTaskItem, FortuneRecord, GameState, NotificationRecipient, Plan, PlanSummary,
    PointLogRecord, ProofAttemptClaim, ProofRecord, ProofResult, PushTokenRecord,
    ScoreEvent, Task, UserProfile,
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
    def get_plan_by_id(self, user_id: str, plan_id: str) -> Optional[Plan]: ...

    @abstractmethod
    def list_plan_summaries(self, user_id: str) -> list[PlanSummary]: ...

    @abstractmethod
    def set_active_plan(self, user_id: str, plan_id: str) -> None: ...

    @abstractmethod
    def create_draft_plan(self, user_id: str, *, name: str, slot_no: int) -> str: ...

    @abstractmethod
    def rename_plan(self, user_id: str, plan_id: str, name: str) -> None: ...

    @abstractmethod
    def plan_belongs_to_user(self, user_id: str, plan_id: str) -> bool: ...

    @abstractmethod
    def count_completed_plans(self, user_id: str) -> int: ...

    @abstractmethod
    def next_plan_slot(self, user_id: str) -> int: ...

    @abstractmethod
    def get_task(self, user_id: str, task_id: str) -> Optional[Task]: ...

    @abstractmethod
    def list_tasks_for_date(self, user_id: str, day: dt_date) -> list[Task]: ...

    @abstractmethod
    def list_daily_tasks_for_date(
        self, user_id: str, day: dt_date
    ) -> list[DailyTaskItem]: ...

    @abstractmethod
    def update_task(self, user_id: str, task: Task) -> None: ...

    @abstractmethod
    def delete_task(self, user_id: str, task_id: str) -> bool:
        """Sahiplik doğrulayarak görevi siler. Yoksa False."""
        ...

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

    def append_chat_messages(self, user_id: str, messages: list[ChatMessage]) -> None:
        """Toplu ekleme — varsayılan tek tek; Supabase tek upsert'e indirger."""
        for message in messages:
            self.append_chat_message(user_id, message)

    @abstractmethod
    def get_chat_history(self, user_id: str) -> list[ChatMessage]: ...

    @abstractmethod
    def clear_chat_history(self, user_id: str) -> int:
        """Aktif oturumun mesajlarını temizler; silinen mesaj sayısını döner."""

    # --- FAZ 7.6: Sohbet oturumları (yeni sohbet ESKİYİ SİLMEZ) ---
    @abstractmethod
    def list_chat_threads(self, user_id: str) -> list[ChatThread]:
        """Sohbet oturumları — en yeniden eskiye, başlıklarıyla."""

    @abstractmethod
    def create_chat_thread(self, user_id: str) -> ChatThread:
        """Yeni oturum açar ve aktif yapar; eski oturumlar korunur."""

    @abstractmethod
    def activate_chat_thread(self, user_id: str, thread_id: str) -> bool:
        """Var olan bir oturuma geçer; bulunamazsa False."""

    @abstractmethod
    def set_active_thread_title(self, user_id: str, title: str) -> None:
        """faz8.13/1b: aktif oturumun başlığını konu özetiyle günceller.

        Degrade kural: thread altyapısı hata verirse sessizce yutulur —
        başlık güncellemesi sohbeti ASLA düşüremez.
        """

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
    def get_latest_intent(self, user_id: str) -> CollectedIntent | None:
        """Aktif veya tamamlanmış son niyet — /plan/next için."""
        ...

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
    def mark_tarot_push_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None: ...

    @abstractmethod
    def mark_recap_push_sent(
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
    def get_subscription_row(self, user_id: str) -> dict: ...

    @abstractmethod
    def update_subscription(
        self,
        user_id: str,
        *,
        subscription_status: str | None = None,
        trial_started_at: datetime | None = None,
    ) -> None: ...

    @abstractmethod
    def delete_account(self, user_id: str) -> None: ...

    # --- V2: Fal modülü (FAZ 7) ---
    @abstractmethod
    def save_fortune(self, user_id: str, record: FortuneRecord) -> None: ...

    @abstractmethod
    def count_fortunes_for_day(
        self, user_id: str, fortune_type: str, day: dt_date
    ) -> int: ...

    @abstractmethod
    def get_fortune_for_day(
        self, user_id: str, fortune_type: str, day: dt_date
    ) -> Optional[FortuneRecord]: ...

    @abstractmethod
    def list_fortunes(self, user_id: str, limit: int = 50) -> list[FortuneRecord]:
        """Fal geçmişi — en yeniden eskiye."""

    # --- faz8.13/4: Online rekabet (opt-in takma adlı lig) ---
    @abstractmethod
    def league_get_member(self, user_id: str) -> Optional[dict]:
        """Kullanıcının lig üyeliği: {alias, score, streak} ya da None."""

    @abstractmethod
    def league_upsert_member(
        self, user_id: str, alias: str, score: int, streak: int
    ) -> None:
        """Üyelik + puan/zincir anlık görüntüsünü yazar (opt-in)."""

    @abstractmethod
    def league_remove_member(self, user_id: str) -> None:
        """Opt-out: üyelik silinir — KVKK gereği iz bırakmaz."""

    @abstractmethod
    def league_top(self, limit: int = 50) -> list[dict]:
        """Puana göre ilk N üye: [{user_id, alias, score, streak}]."""

    # --- İdol Modu persona deposu (Dalga 4.3) ---
    def list_idol_personas(self) -> list[dict]:
        """Aktif persona dosyaları (DB). Varsayılan: boş → dosya kaynağı kullanılır."""
        return []

    def upsert_idol_persona(self, persona: dict, chunks: list[dict]) -> None:
        """Persona + RAG parçalarını yazar (ingest scripti kullanır)."""
        raise NotImplementedError

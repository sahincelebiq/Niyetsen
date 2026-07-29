"""
Niyetsen — Şemalar (API sözleşmeleri + oyun durumu)
Cursor notu: mobil taraf bu şemalara göre tip üretir; alan adlarını değiştirme.
DB'ye geçişte (Supabase) tablolar MASTER_PLAN §2'deki isimlerle eşleşir.
"""
from __future__ import annotations

from datetime import date as dt_date, datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.config import CATEGORIES

Category = Literal["İrade", "İstikrar", "Disiplin", "Özgüven", "Sosyallik", "Özsaygı"]
TaskStatus = Literal["pending", "done", "missed_silent", "missed_excused"]


# ---------- Sohbet / Niyet ----------
class ChatMessage(BaseModel):
    id: Optional[str] = None
    role: Literal["user", "assistant"]
    content: str


class CollectedIntent(BaseModel):
    city: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    weekly_hours: Optional[float] = None
    duration_days: Optional[int] = None
    social_pref: Optional[str] = None
    budget: Optional[str] = None

    def is_ready(self) -> bool:
        """Plan üretimi için asgari alanlar (MASTER_PLAN: şehir + ilgi + zaman)."""
        return bool(self.city and self.interests and self.weekly_hours)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    collected: CollectedIntent = Field(default_factory=CollectedIntent)


class ToolCall(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    ready_for_plan: bool
    collected: CollectedIntent
    crisis: bool = False  # true ise istemci güvenli mod UI gösterir
    message_id: Optional[str] = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # Tek dokunuşluk hızlı yanıtlar (FAZ 7.5) — kullanıcıyı yazarak yormadan akış.
    suggestions: list[str] = Field(default_factory=list)


class ChatSessionResponse(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    collected: CollectedIntent = Field(default_factory=CollectedIntent)
    ready_for_plan: bool = False
    plan_has_content: bool = False
    active_plan_name: str = "Planım"


class ChatGreetingResponse(BaseModel):
    message: str


class AttachmentIngestResponse(BaseModel):
    filename: str
    summary: str
    mime_type: str


# ---------- Plan ----------
class Task(BaseModel):
    id: str
    day: int
    title: str
    task_type: Literal["yer", "alışkanlık", "sosyal", "kişisel_gelişim"] = "alışkanlık"
    categories: list[Category]
    image_keyword: str = ""
    image_url: str = ""
    image_source: str = "placeholder"
    image_attribution: str = ""
    image_attribution_url: str = ""
    duration_min: int = 15
    tiny_version: str = ""  # 2 dakika kuralı — her görevin en küçük halkası
    status: TaskStatus = "pending"
    date: Optional[dt_date] = None
    proof_id: Optional[str] = None


class PlanDay(BaseModel):
    day: int
    theme: str = ""
    tasks: list[Task]


class Plan(BaseModel):
    id: str
    duration_days: int
    batch_generated_until: int  # kaçıncı güne kadar üretildi (partili üretim)
    start_date: dt_date  # gün 1'in takvim tarihi; her Task.date buradan türer
    days: list[PlanDay]
    name: str = "Planım"
    slot_no: int = 1
    is_active: bool = True


class PlanSummary(BaseModel):
    id: str
    name: str
    slot_no: int
    is_active: bool
    has_content: bool


class PlanRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=48)


class DailyTaskItem(BaseModel):
    plan_id: str
    plan_name: str
    task: Task


class PlanGenerateRequest(BaseModel):
    collected: CollectedIntent
    duration_days: int = 365


# ---------- Kanıt ----------
class ProofResult(BaseModel):
    approved: bool
    confidence: int
    reason: str
    attempt_no: int
    accepted_by_declaration: bool = False  # 3. denemede kullanıcı beyanıyla kabul
    proof_id: Optional[str] = None
    photo_url: Optional[str] = None


class ProofRecord(BaseModel):
    id: str
    task_id: str
    photo_url: str
    location: Optional[dict[str, float]] = None
    confidence_score: int = Field(ge=0, le=100)
    attempt_no: int = Field(ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProofAttemptClaim(BaseModel):
    status: Literal["started", "in_progress", "completed"]
    attempt_no: int
    result: Optional[ProofResult] = None


# ---------- Oyun durumu ----------
class GameState(BaseModel):
    """Bir kullanıcının tüm oyunlaştırma durumu. Saf mantık bunun üstünde çalışır."""
    user_id: str
    points: dict[str, int] = Field(default_factory=lambda: {c: 0 for c in CATEGORIES})
    silent_miss_streak: int = 0
    excuse_count: int = 0
    streak_len: int = 0
    best_streak: int = 0
    last_active_date: Optional[dt_date] = None
    freeze_tokens: int = 0  # ilk jeton ay başı otomatik hibesinden gelir
    freeze_last_grant: Optional[str] = None  # "YYYY-MM"


class ScoreEvent(BaseModel):
    """Her puan hareketi loglanır (point_log tablosunun karşılığı)."""
    category: str
    delta: int
    reason: str


class PointLogRecord(ScoreEvent):
    id: Optional[str] = None
    user_id: str
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CronUser(BaseModel):
    user_id: str
    timezone: str = "Europe/Istanbul"


class StateResponse(BaseModel):
    points: dict[str, int]
    ranks: dict[str, str]
    overall_rank: str
    streak_len: int
    best_streak: int
    freeze_tokens: int
    excuse_count: int
    silent_miss_streak: int


# ---------- Profil / Onboarding ----------
class UserProfile(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[dt_date] = None
    zodiac_sign: Optional[str] = None
    # FAZ 8: sohbet kişiselleştirmesi için İSTEĞE BAĞLI cinsiyet (KVKK: zorunlu
    # değil, sadece hitap/örnek uyarlaması için; klişe üretimi prompt'ta yasak).
    gender: Optional[Literal["kadın", "erkek", "belirtmek istemiyorum"]] = None
    timezone: str = "Europe/Istanbul"
    notif_hour: int = 8
    notif_minute: int = 0
    irade_modu_active: bool = False
    kvkk_consent_at: Optional[datetime] = None
    onboarding_complete: bool = False


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: dt_date
    gender: Optional[Literal["kadın", "erkek", "belirtmek istemiyorum"]] = None
    timezone: str = Field(default="Europe/Istanbul", min_length=1, max_length=80)
    notif_hour: int = Field(default=8, ge=0, le=23)
    notif_minute: int = Field(default=0, ge=0, le=59)
    # Legacy onboarding clients may still send true. Omitted/false never revokes
    # consent; revocation belongs to the explicit /me/consent endpoint.
    kvkk_consent: Optional[bool] = None
    irade_modu_active: bool = False


# ---------- Abonelik / Deneme (FAZ 5) ----------
SubscriptionStatus = Literal["free", "trial", "active", "expired", "cancelled"]


class SubscriptionInfo(BaseModel):
    status: SubscriptionStatus = "free"
    trial_started_at: Optional[datetime] = None
    trial_days_remaining: int = 0
    has_premium_access: bool = True
    show_paywall: bool = False


class RevenueCatWebhookPayload(BaseModel):
    """RevenueCat webhook gövdesinin minimal alt kümesi."""
    event: dict = Field(default_factory=dict)


# ---------- Versioned legal consent ----------
ConsentKind = Literal[
    "privacy_policy",
    "kvkk_explicit_consent",
    "ai_chat_processing",
    "proof_photo_processing",
    "marketing_communications",
]


class ConsentRecord(BaseModel):
    kind: ConsentKind
    version: str
    accepted: bool
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentChoice(BaseModel):
    accepted: bool


class ConsentUpdate(BaseModel):
    privacy_policy: Optional[ConsentChoice] = None
    kvkk_explicit_consent: Optional[ConsentChoice] = None
    ai_chat_processing: Optional[ConsentChoice] = None
    proof_photo_processing: Optional[ConsentChoice] = None
    marketing_communications: Optional[ConsentChoice] = None


class ConsentItem(BaseModel):
    version: str
    accepted: bool = False
    decided_at: Optional[datetime] = None
    required_for: list[str] = Field(default_factory=list)


class ConsentStatus(BaseModel):
    data_controller: str
    contact_email: str
    needs_reconsent: bool = False
    privacy_policy: ConsentItem
    kvkk_explicit_consent: ConsentItem
    ai_chat_processing: ConsentItem
    proof_photo_processing: ConsentItem
    marketing_communications: ConsentItem


# ---------- Push notifications / bonus tasks ----------
class PushTokenRegistration(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    platform: Literal["ios", "android"]


class PushTokenRecord(PushTokenRegistration):
    user_id: str
    enabled: bool = True
    last_task_reminder_date: Optional[dt_date] = None
    last_bonus_offer_date: Optional[dt_date] = None
    last_tarot_push_date: Optional[dt_date] = None


class NotificationRecipient(BaseModel):
    user_id: str
    timezone: str = "Europe/Istanbul"
    notif_hour: int = Field(default=8, ge=0, le=23)
    notif_minute: int = Field(default=0, ge=0, le=59)
    token: str
    last_task_reminder_date: Optional[dt_date] = None
    last_bonus_offer_date: Optional[dt_date] = None
    last_tarot_push_date: Optional[dt_date] = None


BonusStatus = Literal["offered", "completed", "expired"]


class BonusOffer(BaseModel):
    id: str
    user_id: str
    bonus_key: str
    title: str
    tiny_instruction: str
    category: Category
    day: dt_date
    status: BonusStatus = "offered"
    completion_id: Optional[str] = None
    offered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class BonusCompletionRequest(BaseModel):
    completion_id: str = Field(min_length=8, max_length=128)


class BonusOfferResponse(BaseModel):
    id: str
    title: str
    tiny_instruction: str
    category: Category
    day: dt_date
    status: BonusStatus
    points: int


# ---------- V2: Fal modülü (FAZ 7) ----------
FortuneType = Literal["tarot", "kahve", "el", "burc"]

FORTUNE_DISCLAIMER = (
    "Bu içerik eğlence amaçlıdır; kader tayini, tıbbi, hukuki veya finansal "
    "tavsiye değildir."
)


class TarotCardResult(BaseModel):
    name: str
    position: str                     # geçmiş | şimdi | niyetin yönü
    reversed: bool = False
    meaning: str = ""


class FortuneRecord(BaseModel):
    id: str
    type: FortuneType
    day: dt_date
    result: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FortuneRightsItem(BaseModel):
    limit: int                        # -1 = sınırsız
    used: int
    remaining: int                    # -1 = sınırsız


class FortuneRightsResponse(BaseModel):
    is_premium: bool
    rights: dict[str, FortuneRightsItem]
    disclaimer: str = FORTUNE_DISCLAIMER


class TarotDrawRequest(BaseModel):
    question: str = Field(default="", max_length=280)


class TarotDrawResponse(BaseModel):
    cards: list[TarotCardResult]
    interpretation: str
    already_drawn_today: bool = False
    disclaimer: str = FORTUNE_DISCLAIMER


class PhotoFortuneResponse(BaseModel):
    kind: Literal["kahve", "el"]
    symbols: list[str] = Field(default_factory=list)
    interpretation: str
    remaining_today: int
    disclaimer: str = FORTUNE_DISCLAIMER


class HoroscopeResponse(BaseModel):
    sign: str
    day: dt_date
    interpretation: str
    disclaimer: str = FORTUNE_DISCLAIMER


# ---------- FAZ 7.6: Sohbet oturumları (Claude tarzı) ----------
class ChatThread(BaseModel):
    id: str
    title: str = ""                    # boşsa istemci "Yeni sohbet" gösterir
    is_active: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

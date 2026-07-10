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


class ChatSessionResponse(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    collected: CollectedIntent = Field(default_factory=CollectedIntent)
    ready_for_plan: bool = False


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
    timezone: str = "Europe/Istanbul"
    notif_hour: int = 8
    irade_modu_active: bool = False
    kvkk_consent_at: Optional[datetime] = None
    onboarding_complete: bool = False


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    birth_date: dt_date
    timezone: str = Field(default="Europe/Istanbul", min_length=1, max_length=80)
    notif_hour: int = Field(default=8, ge=0, le=23)
    kvkk_consent: bool = False
    irade_modu_active: bool = False

"""
Niyetsen — Supabase Depolama Katmanı (Faz 2 yuvası)
Repository arayüzünün gerçek DB implementasyonu. Tablolar: NIYETSEN_MASTER_PLAN §2
(users, streaks, points, plans, tasks — migration: niyetsen_core_tables).
service_role anahtarıyla çalışır → RLS bypass edilir; erişim kontrolü bu backend'in
üstünde (JWT middleware, api/routes.py > get_current_user).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from supabase import Client, create_client

from app.config import CATEGORIES, settings
from app.models.schemas import (
    ChatMessage, CollectedIntent, CronUser, GameState, Plan, PlanDay,
    PointLogRecord, ProofRecord, ScoreEvent, Task, UserProfile,
)
from app.storage.base import Repository

log = logging.getLogger("niyetsen.storage")


def _maybe_single(builder) -> Optional[dict]:
    """postgrest-py: .maybe_single().execute() sıfır satırda None DÖNER (response
    nesnesi değil) — doğrudan .data çağırmak AttributeError patlatır."""
    response = builder.maybe_single().execute()
    return response.data if response is not None else None


def _task_from_row(row: dict) -> Task:
    return Task(
        id=row["id"],
        day=row["day_no"],
        title=row["title"],
        task_type=row["task_type"],
        categories=row["categories"],
        image_keyword=row["image_keyword"],
        image_url=row["image_url"],
        image_source=row.get("image_source", "placeholder"),
        image_attribution=row.get("image_attribution", ""),
        image_attribution_url=row.get("image_attribution_url", ""),
        duration_min=row["duration_min"],
        tiny_version=row["tiny_version"],
        status=row["status"],
        date=row["date"],
        proof_id=row.get("proof_id"),
    )


def _task_row(plan_id: str, day: PlanDay, task: Task) -> dict:
    return {
        "id": task.id,
        "plan_id": plan_id,
        "day_no": day.day,
        "day_theme": day.theme,
        "date": task.date.isoformat() if task.date else None,
        "title": task.title,
        "task_type": task.task_type,
        "categories": task.categories,
        "image_keyword": task.image_keyword,
        "image_url": task.image_url,
        "image_source": task.image_source,
        "image_attribution": task.image_attribution,
        "image_attribution_url": task.image_attribution_url,
        "duration_min": task.duration_min,
        "tiny_version": task.tiny_version,
        "status": task.status,
        # proof_attempts kasıtlı olarak dahil edilmedi: upsert on-conflict bu alana
        # dokunmasın, var olan deneme sayısı korunsun (/plan/next tüm planı yeniden yazar).
    }


class SupabaseRepository(Repository):
    def __init__(self) -> None:
        self._db: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    # ------------------------------------------------------------------
    # Oyun durumu
    # ------------------------------------------------------------------
    def get_state(self, user_id: str) -> GameState:
        self._ensure_user(user_id)

        points = {c: 0 for c in CATEGORIES}
        for row in self._db.table("points").select("category,value").eq("user_id", user_id).execute().data:
            if row["category"] in points:
                points[row["category"]] = row["value"]

        streak_row = _maybe_single(
            self._db.table("streaks").select("*").eq("user_id", user_id)
        ) or {}
        user_row = (
            self._db.table("users").select("excuse_count,freeze_tokens,freeze_last_grant")
            .eq("id", user_id).single().execute().data
        )

        return GameState(
            user_id=user_id,
            points=points,
            silent_miss_streak=streak_row.get("silent_miss_streak", 0),
            excuse_count=user_row["excuse_count"],
            streak_len=streak_row.get("current_len", 0),
            best_streak=streak_row.get("best_len", 0),
            last_active_date=streak_row.get("last_active_date"),
            freeze_tokens=user_row["freeze_tokens"],
            freeze_last_grant=user_row["freeze_last_grant"],
        )

    def save_state(self, state: GameState) -> None:
        self._ensure_user(state.user_id)

        self._db.table("users").update({
            "excuse_count": state.excuse_count,
            "freeze_tokens": state.freeze_tokens,
            "freeze_last_grant": state.freeze_last_grant,
        }).eq("id", state.user_id).execute()

        self._db.table("streaks").upsert({
            "user_id": state.user_id,
            "current_len": state.streak_len,
            "best_len": state.best_streak,
            "last_active_date": state.last_active_date.isoformat() if state.last_active_date else None,
            "silent_miss_streak": state.silent_miss_streak,
        }).execute()

        self._db.table("points").upsert([
            {"user_id": state.user_id, "category": c, "value": v}
            for c, v in state.points.items()
        ]).execute()

    def _ensure_user(self, user_id: str) -> None:
        existing = self._db.table("users").select("id").eq("id", user_id).execute().data
        if not existing:
            self._db.table("users").insert({"id": user_id}).execute()

    # ------------------------------------------------------------------
    # Plan / Görev
    # ------------------------------------------------------------------
    def save_plan(self, user_id: str, plan: Plan) -> None:
        self._ensure_user(user_id)
        self._db.table("plans").upsert({
            "id": plan.id,
            "user_id": user_id,
            "duration_days": plan.duration_days,
            "batch_generated_until": plan.batch_generated_until,
            "start_date": plan.start_date.isoformat(),
        }, on_conflict="user_id").execute()

        rows = [_task_row(plan.id, day, t) for day in plan.days for t in day.tasks]
        if rows:
            self._db.table("tasks").upsert(rows, on_conflict="id").execute()

    def get_plan(self, user_id: str) -> Optional[Plan]:
        plan_row = _maybe_single(self._db.table("plans").select("*").eq("user_id", user_id))
        if not plan_row:
            return None

        task_rows = (
            self._db.table("tasks").select("*").eq("plan_id", plan_row["id"])
            .order("day_no").execute().data
        )
        days: dict[int, PlanDay] = {}
        for row in task_rows:
            day = days.setdefault(row["day_no"], PlanDay(day=row["day_no"], theme=row["day_theme"], tasks=[]))
            day.tasks.append(_task_from_row(row))

        return Plan(
            id=plan_row["id"],
            duration_days=plan_row["duration_days"],
            batch_generated_until=plan_row["batch_generated_until"],
            start_date=plan_row["start_date"],
            days=[days[k] for k in sorted(days)],
        )

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        # plans!inner ile sahiplik doğrulanır: başka kullanıcının task_id'siyle sızma olmaz.
        row = _maybe_single(
            self._db.table("tasks").select("*, plans!inner(user_id)")
            .eq("id", task_id).eq("plans.user_id", user_id)
        )
        return _task_from_row(row) if row else None

    def update_task(self, user_id: str, task: Task) -> None:
        if self.get_task(user_id, task.id) is None:
            return
        self._db.table("tasks").update({
            "title": task.title,
            "task_type": task.task_type,
            "categories": task.categories,
            "image_keyword": task.image_keyword,
            "image_url": task.image_url,
            "image_source": task.image_source,
            "image_attribution": task.image_attribution,
            "image_attribution_url": task.image_attribution_url,
            "duration_min": task.duration_min,
            "tiny_version": task.tiny_version,
            "status": task.status,
            "date": task.date.isoformat() if task.date else None,
            "proof_id": task.proof_id,
        }).eq("id", task.id).execute()

    # ------------------------------------------------------------------
    # Kanıt denemeleri
    # ------------------------------------------------------------------
    def get_proof_attempts(self, user_id: str, task_id: str) -> int:
        if self.get_task(user_id, task_id) is None:
            return 0
        row = _maybe_single(self._db.table("tasks").select("proof_attempts").eq("id", task_id))
        return (row or {}).get("proof_attempts", 0)

    def incr_proof_attempts(self, user_id: str, task_id: str) -> int:
        if self.get_task(user_id, task_id) is None:
            return 0
        new_val = self.get_proof_attempts(user_id, task_id) + 1
        self._db.table("tasks").update({"proof_attempts": new_val}).eq("id", task_id).execute()
        return new_val

    def store_proof_photo(
        self, user_id: str, task_id: str, image_bytes: bytes, mime_type: str
    ) -> str:
        if self.get_task(user_id, task_id) is None:
            raise ValueError("Görev kullanıcıya ait değil.")
        extension = "jpg" if mime_type == "image/jpeg" else "png"
        path = f"{user_id}/{uuid.uuid4()}.{extension}"
        self._db.storage.from_("proofs").upload(
            path,
            image_bytes,
            file_options={"content-type": mime_type, "upsert": "false"},
        )
        # Bucket private olduğu için kalıcı public URL üretmeyiz. Bu değer nesne
        # adresidir; görüntüleme gerektiğinde kısa ömürlü signed URL oluşturulur.
        return f"storage://proofs/{path}"

    def save_proof(self, user_id: str, proof: ProofRecord) -> None:
        if self.get_task(user_id, proof.task_id) is None:
            raise ValueError("Görev kullanıcıya ait değil.")
        self._db.table("proofs").insert({
            "id": proof.id,
            "task_id": proof.task_id,
            "photo_url": proof.photo_url,
            "location": proof.location,
            "confidence_score": proof.confidence_score,
            "attempt_no": proof.attempt_no,
            "created_at": proof.created_at.isoformat(),
        }).execute()

    def get_proofs(self, user_id: str, task_id: str) -> list[ProofRecord]:
        if self.get_task(user_id, task_id) is None:
            return []
        rows = (
            self._db.table("proofs").select("*").eq("task_id", task_id)
            .order("attempt_no").execute().data
        )
        return [ProofRecord(**row) for row in rows]

    def append_point_log(
        self, user_id: str, task_id: str | None, events: list[ScoreEvent]
    ) -> None:
        if not events:
            return
        self._ensure_user(user_id)
        self._db.table("point_log").insert([
            {
                "user_id": user_id,
                "task_id": task_id,
                "category": event.category,
                "delta": event.delta,
                "reason": event.reason,
            }
            for event in events
        ]).execute()

    def get_point_log(self, user_id: str) -> list[PointLogRecord]:
        rows = (
            self._db.table("point_log").select("*").eq("user_id", user_id)
            .order("created_at").execute().data
        )
        return [PointLogRecord(**row) for row in rows]

    def list_cron_users(self) -> list[CronUser]:
        rows: list[dict] = []
        page_size = 1000
        while True:
            page = (
                self._db.table("users").select("id,timezone")
                .range(len(rows), len(rows) + page_size - 1)
                .execute().data
            )
            rows.extend(page)
            if len(page) < page_size:
                break
        return [
            CronUser(user_id=row["id"], timezone=row.get("timezone") or "Europe/Istanbul")
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Sohbet geçmişi + niyet (Faz 2)
    # ------------------------------------------------------------------
    def append_chat_message(self, user_id: str, message: ChatMessage) -> None:
        self._ensure_user(user_id)
        row = {
            "user_id": user_id,
            "client_message_id": message.id,
            "role": message.role,
            "content": message.content,
        }
        if message.id:
            self._db.table("chat_msgs").upsert(
                row,
                on_conflict="user_id,client_message_id",
                ignore_duplicates=True,
            ).execute()
        else:
            self._db.table("chat_msgs").insert(row).execute()

    def get_chat_history(self, user_id: str) -> list[ChatMessage]:
        rows = (
            self._db.table("chat_msgs").select("id,client_message_id,role,content")
            .eq("user_id", user_id).order("created_at").execute().data
        )
        return [
            ChatMessage(
                id=row.get("client_message_id") or f"legacy-{row['id']}",
                role=row["role"],
                content=row["content"],
            )
            for row in rows
        ]

    def save_intent(
        self,
        user_id: str,
        collected: CollectedIntent,
        duration_days: int,
        ready_for_plan: bool = False,
    ) -> None:
        self._ensure_user(user_id)
        payload = json.dumps({
            "collected": collected.model_dump(mode="json"),
            "ready_for_plan": ready_for_plan,
        }, ensure_ascii=False)
        active = _maybe_single(
            self._db.table("intents").select("id").eq("user_id", user_id)
            .eq("status", "active").order("created_at", desc=True).limit(1)
        )
        values = {
            "text": payload,
            "duration_days": duration_days,
        }
        if active:
            self._db.table("intents").update(values).eq("id", active["id"]).execute()
        else:
            self._db.table("intents").insert({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                **values,
            }).execute()

    def get_active_intent(self, user_id: str) -> tuple[CollectedIntent, bool] | None:
        active = _maybe_single(
            self._db.table("intents").select("text").eq("user_id", user_id)
            .eq("status", "active").order("created_at", desc=True).limit(1)
        )
        if not active:
            return None
        try:
            payload = json.loads(active["text"])
            return (
                CollectedIntent(**payload.get("collected", {})),
                bool(payload.get("ready_for_plan", False)),
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return CollectedIntent(), False

    def complete_active_intent(self, user_id: str) -> None:
        self._db.table("intents").update({"status": "done"}).eq(
            "user_id", user_id
        ).eq("status", "active").execute()

    # ------------------------------------------------------------------
    # Profil / hesap yaşam döngüsü (Faz 2)
    # ------------------------------------------------------------------
    def get_profile(self, user_id: str) -> UserProfile:
        self._ensure_user(user_id)
        row = self._db.table("users").select(
            "name,birth_date,zodiac_sign,timezone,notif_hour,"
            "irade_modu_active,kvkk_consent_at"
        ).eq("id", user_id).single().execute().data
        complete = bool(
            row.get("name")
            and row.get("birth_date")
            and row.get("kvkk_consent_at")
        )
        return UserProfile(**row, onboarding_complete=complete)

    def save_profile(self, user_id: str, profile: UserProfile) -> None:
        self._ensure_user(user_id)
        self._db.table("users").update({
            "name": profile.name,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "zodiac_sign": profile.zodiac_sign,
            "timezone": profile.timezone,
            "notif_hour": profile.notif_hour,
            "irade_modu_active": profile.irade_modu_active,
            "kvkk_consent_at": (
                profile.kvkk_consent_at.isoformat()
                if profile.kvkk_consent_at else None
            ),
        }).eq("id", user_id).execute()

    def delete_account(self, user_id: str) -> None:
        # Storage önce: DB/Auth silinirse sahipliği sonradan bulmak zorlaşır.
        try:
            bucket = self._db.storage.from_("proofs")
            files = bucket.list(path=user_id)
            paths = [
                f"{user_id}/{item['name']}"
                for item in files
                if item.get("name")
            ]
            if paths:
                bucket.remove(paths)
        except Exception as exc:  # bucket Faz 3'e kadar bulunmayabilir
            log.info("Proof storage temizliği atlandı (%s): %s", user_id, exc)

        self._db.table("users").delete().eq("id", user_id).execute()
        try:
            self._db.auth.admin.delete_user(user_id)
        except Exception as exc:
            raise RuntimeError(
                "Veriler silindi ancak Auth hesabı silinemedi; yönetici kontrolü gerekli."
            ) from exc

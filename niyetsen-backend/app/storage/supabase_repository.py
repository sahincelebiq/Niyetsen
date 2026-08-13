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
from datetime import date as dt_date, datetime, timezone
from typing import Optional

from supabase import Client, ClientOptions, create_client

from app.config import CATEGORIES, settings
from app.models.schemas import (
    BonusOffer, ChatMessage, ChatThread, CollectedIntent, ConsentRecord, CronUser,
    DailyTaskItem, FortuneRecord, GameState, NotificationRecipient, Plan, PlanDay,
    PlanSummary, PointLogRecord, ProofAttemptClaim, ProofRecord, ProofResult,
    PushTokenRecord, ScoreEvent, Task, UserProfile,
)
from app.core.datetimes import coerce_datetime
from app.storage.base import Repository
from app.storage.db_coerce import is_unique_violation, parse_json_object

log = logging.getLogger("niyetsen.storage")


def _maybe_single(builder) -> Optional[dict]:
    """postgrest-py: .maybe_single().execute() sıfır satırda None DÖNER (response
    nesnesi değil) — doğrudan .data çağırmak AttributeError patlatır."""
    response = builder.maybe_single().execute()
    return response.data if response is not None else None


def _parse_optional_date(value) -> dt_date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt_date):
        return value
    return dt_date.fromisoformat(str(value))


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


def _fortune_from_row(row: dict) -> FortuneRecord:
    return FortuneRecord(
        id=row["id"],
        type=row["type"],
        day=row["day"],
        result=parse_json_object(row.get("result_json")),
        created_at=coerce_datetime(row.get("created_at")) or datetime.now(timezone.utc),
    )


def _bonus_from_row(row: dict) -> BonusOffer:
    payload = dict(row)
    offered = coerce_datetime(payload.get("offered_at"))
    if offered is not None:
        payload["offered_at"] = offered
    completed = coerce_datetime(payload.get("completed_at"))
    payload["completed_at"] = completed
    return BonusOffer(**payload)


class SupabaseRepository(Repository):
    def __init__(self) -> None:
        timeout_sec = settings.SUPABASE_TIMEOUT_SEC
        self._db: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            options=ClientOptions(
                postgrest_client_timeout=timeout_sec,
                storage_client_timeout=min(timeout_sec, 60),
            ),
        )

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
        user_row = _maybe_single(
            self._db.table("users").select("excuse_count,freeze_tokens,freeze_last_grant")
            .eq("id", user_id)
        ) or {}

        last_active = streak_row.get("last_active_date")
        if last_active is not None and not isinstance(last_active, dt_date):
            last_active = dt_date.fromisoformat(str(last_active))

        return GameState(
            user_id=user_id,
            points=points,
            silent_miss_streak=streak_row.get("silent_miss_streak", 0),
            excuse_count=user_row.get("excuse_count") or 0,
            streak_len=streak_row.get("current_len", 0),
            best_streak=streak_row.get("best_len", 0),
            last_active_date=last_active,
            freeze_tokens=user_row.get("freeze_tokens") or 0,
            freeze_last_grant=user_row.get("freeze_last_grant"),
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
        if existing:
            return
        try:
            self._db.table("users").insert({"id": user_id}).execute()
        except Exception as exc:  # noqa: BLE001 — eşzamanlı ilk istek
            if is_unique_violation(exc):
                return
            raise

    # ------------------------------------------------------------------
    # Plan / Görev
    # ------------------------------------------------------------------
    def _active_plan_id(self, user_id: str) -> Optional[str]:
        row = _maybe_single(
            self._db.table("users").select("active_plan_id").eq("id", user_id)
        )
        return row.get("active_plan_id") if row else None

    def _set_active_plan_id(self, user_id: str, plan_id: str) -> None:
        self._db.table("users").update({"active_plan_id": plan_id}).eq("id", user_id).execute()

    def _plan_row_to_model(self, plan_row: dict, user_id: str) -> Plan:
        task_rows = (
            self._db.table("tasks").select("*").eq("plan_id", plan_row["id"])
            .order("day_no").execute().data
        )
        days: dict[int, PlanDay] = {}
        for row in task_rows:
            day = days.setdefault(
                row["day_no"],
                PlanDay(day=row["day_no"], theme=row["day_theme"], tasks=[]),
            )
            day.tasks.append(_task_from_row(row))
        active_id = self._active_plan_id(user_id)
        return Plan(
            id=plan_row["id"],
            duration_days=plan_row["duration_days"],
            batch_generated_until=plan_row["batch_generated_until"],
            start_date=plan_row["start_date"],
            days=[days[k] for k in sorted(days)],
            name=plan_row.get("name") or "Planım",
            slot_no=plan_row.get("slot_no") or 1,
            is_active=plan_row["id"] == active_id,
        )

    def save_plan(self, user_id: str, plan: Plan) -> None:
        self._ensure_user(user_id)
        self._db.table("plans").upsert({
            "id": plan.id,
            "user_id": user_id,
            "duration_days": plan.duration_days,
            "batch_generated_until": plan.batch_generated_until,
            "start_date": plan.start_date.isoformat(),
            "name": plan.name,
            "slot_no": plan.slot_no,
        }, on_conflict="id").execute()
        self._set_active_plan_id(user_id, plan.id)

        rows = [_task_row(plan.id, day, t) for day in plan.days for t in day.tasks]
        if rows:
            self._db.table("tasks").upsert(rows, on_conflict="id").execute()

    def get_plan(self, user_id: str) -> Optional[Plan]:
        active_id = self._active_plan_id(user_id)
        if active_id:
            plan_row = _maybe_single(
                self._db.table("plans").select("*").eq("id", active_id).eq("user_id", user_id)
            )
            if plan_row:
                plan = self._plan_row_to_model(plan_row, user_id)
                return plan if plan.days else None
        plan_row = _maybe_single(
            self._db.table("plans").select("*").eq("user_id", user_id)
            .order("slot_no").limit(1)
        )
        if not plan_row:
            return None
        self._set_active_plan_id(user_id, plan_row["id"])
        plan = self._plan_row_to_model(plan_row, user_id)
        return plan if plan.days else None

    def get_plan_by_id(self, user_id: str, plan_id: str) -> Optional[Plan]:
        plan_row = _maybe_single(
            self._db.table("plans").select("*").eq("id", plan_id).eq("user_id", user_id)
        )
        if not plan_row:
            return None
        plan = self._plan_row_to_model(plan_row, user_id)
        return plan if plan.days else None

    def list_plan_summaries(self, user_id: str) -> list[PlanSummary]:
        self._ensure_user(user_id)
        active_id = self._active_plan_id(user_id)
        rows = (
            self._db.table("plans").select("id,name,slot_no,batch_generated_until")
            .eq("user_id", user_id).order("slot_no").execute().data
        )
        if not rows:
            try:
                self.create_draft_plan(user_id, name="Plan 1", slot_no=1)
            except Exception as exc:  # noqa: BLE001
                log.warning("Taslak plan oluşturulamadı (okuma yolu yutuyor): %s", exc)
            rows = (
                self._db.table("plans").select("id,name,slot_no,batch_generated_until")
                .eq("user_id", user_id).order("slot_no").execute().data
            ) or []
            if rows:
                active_id = self._active_plan_id(user_id) or rows[0]["id"]
        summaries: list[PlanSummary] = []
        for row in rows:
            task_count = (
                self._db.table("tasks").select("id", count="exact")
                .eq("plan_id", row["id"]).limit(1).execute()
            )
            has_content = bool(task_count.count)
            summaries.append(
                PlanSummary(
                    id=row["id"],
                    name=row.get("name") or "Planım",
                    slot_no=row.get("slot_no") or 1,
                    is_active=row["id"] == active_id,
                    has_content=has_content,
                )
            )
        return summaries

    def set_active_plan(self, user_id: str, plan_id: str) -> None:
        if not self.plan_belongs_to_user(user_id, plan_id):
            raise ValueError("Plan bulunamadı.")
        self._set_active_plan_id(user_id, plan_id)
        # Plana bağlı en güncel sohbet oturumuna geç (yoksa yeni açılır) —
        # FAZ 7.6: proje değişince o projenin sohbeti gelir.
        # FAZ 8 dayanıklılık: thread tarafı hata verirse PLAN GEÇİŞİ YİNE
        # BAŞARILIDIR (toplantıdaki "planlar arası geçiş yapamıyorum"
        # hatasının olası kök nedeni buydu).
        try:
            row = _maybe_single(
                self._db.table("chat_threads").select("id")
                .eq("user_id", user_id).eq("plan_id", plan_id)
                .order("updated_at", desc=True).limit(1)
            )
            if row:
                self._db.table("users").update(
                    {"active_thread_id": row["id"]}
                ).eq("id", user_id).execute()
            else:
                self._create_thread_row(user_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Plan geçişinde thread ayarlanamadı (yoksayıldı): %s", exc)

    def create_draft_plan(self, user_id: str, *, name: str, slot_no: int) -> str:
        self._ensure_user(user_id)
        existing = _maybe_single(
            self._db.table("plans").select("id")
            .eq("user_id", user_id).eq("slot_no", slot_no)
        )
        if existing:
            self._set_active_plan_id(user_id, existing["id"])
            return existing["id"]
        plan_id = str(uuid.uuid4())
        try:
            self._db.table("plans").insert({
                "id": plan_id,
                "user_id": user_id,
                "duration_days": 365,
                "batch_generated_until": 0,
                "start_date": dt_date.today().isoformat(),
                "name": name,
                "slot_no": slot_no,
            }).execute()
        except Exception as exc:  # noqa: BLE001
            if is_unique_violation(exc):
                raced = _maybe_single(
                    self._db.table("plans").select("id")
                    .eq("user_id", user_id).eq("slot_no", slot_no)
                )
                if raced:
                    self._set_active_plan_id(user_id, raced["id"])
                    return raced["id"]
            raise
        self._set_active_plan_id(user_id, plan_id)
        return plan_id

    def rename_plan(self, user_id: str, plan_id: str, name: str) -> None:
        if not self.plan_belongs_to_user(user_id, plan_id):
            raise ValueError("Plan bulunamadı.")
        self._db.table("plans").update({"name": name}).eq("id", plan_id).execute()

    def plan_belongs_to_user(self, user_id: str, plan_id: str) -> bool:
        row = _maybe_single(
            self._db.table("plans").select("id").eq("id", plan_id).eq("user_id", user_id)
        )
        return row is not None

    def count_completed_plans(self, user_id: str) -> int:
        rows = self._db.table("plans").select("id").eq("user_id", user_id).execute().data
        count = 0
        for row in rows:
            tasks = (
                self._db.table("tasks").select("id", count="exact")
                .eq("plan_id", row["id"]).limit(1).execute()
            )
            if tasks.count:
                count += 1
        return count

    def next_plan_slot(self, user_id: str) -> int:
        rows = self._db.table("plans").select("slot_no").eq("user_id", user_id).execute().data
        slots = [row.get("slot_no") or 1 for row in rows]
        return (max(slots) if slots else 0) + 1

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        # plans!inner ile sahiplik doğrulanır: başka kullanıcının task_id'siyle sızma olmaz.
        row = _maybe_single(
            self._db.table("tasks").select("*, plans!inner(user_id)")
            .eq("id", task_id).eq("plans.user_id", user_id)
        )
        return _task_from_row(row) if row else None

    def _plan_ids_for_user(self, user_id: str) -> list[str]:
        rows = (
            self._db.table("plans").select("id").eq("user_id", user_id).execute().data
        )
        return [row["id"] for row in rows]

    def list_tasks_for_date(self, user_id: str, day: dt_date) -> list[Task]:
        plan_ids = self._plan_ids_for_user(user_id)
        if not plan_ids:
            return []
        rows = (
            self._db.table("tasks").select("*")
            .in_("plan_id", plan_ids)
            .eq("date", day.isoformat())
            .execute().data
        )
        return [_task_from_row(row) for row in rows]

    def list_daily_tasks_for_date(
        self, user_id: str, day: dt_date
    ) -> list[DailyTaskItem]:
        plans = (
            self._db.table("plans").select("id,name")
            .eq("user_id", user_id).execute().data
        )
        if not plans:
            return []
        plan_names = {row["id"]: row.get("name") or "Planım" for row in plans}
        plan_ids = list(plan_names)
        rows = (
            self._db.table("tasks").select("*")
            .in_("plan_id", plan_ids)
            .eq("date", day.isoformat())
            .execute().data
        )
        return [
            DailyTaskItem(
                plan_id=row["plan_id"],
                plan_name=plan_names.get(row["plan_id"], "Planım"),
                task=_task_from_row(row),
            )
            for row in rows
        ]

    def update_task(self, user_id: str, task: Task) -> None:
        if self.get_task(user_id, task.id) is None:
            return
        self._db.table("tasks").update({
            "title": task.title,
            "day_no": task.day,
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

    def delete_task(self, user_id: str, task_id: str) -> bool:
        # plans!inner ile sahiplik; başka kullanıcının task_id'si silinmez.
        if self.get_task(user_id, task_id) is None:
            return False
        self._db.table("tasks").delete().eq("id", task_id).execute()
        return True

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

    def begin_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> ProofAttemptClaim:
        rows = self._db.rpc("claim_proof_attempt", {
            "p_user_id": user_id,
            "p_task_id": task_id,
            "p_idempotency_key": idempotency_key,
        }).execute().data
        row = rows[0] if isinstance(rows, list) else rows
        if not row:
            raise ValueError("Görev bulunamadı.")
        if row.get("claim_status") == "not_found":
            raise ValueError("Görev bulunamadı.")
        if row.get("claim_status") == "resolved":
            raise RuntimeError("Görev zaten sonuçlanmış.")
        result_payload = parse_json_object(row.get("result_json")) if row.get("result_json") else {}
        result = ProofResult(**result_payload) if result_payload else None
        return ProofAttemptClaim(
            status=row["claim_status"],
            attempt_no=row["attempt_no"],
            result=result,
        )

    def finish_proof_attempt(
        self,
        user_id: str,
        task_id: str,
        idempotency_key: str,
        result: ProofResult,
    ) -> None:
        self._db.rpc("finish_proof_attempt", {
            "p_user_id": user_id,
            "p_task_id": task_id,
            "p_idempotency_key": idempotency_key,
            "p_result": result.model_dump(mode="json"),
        }).execute()

    def abort_proof_attempt(
        self, user_id: str, task_id: str, idempotency_key: str
    ) -> None:
        self._db.rpc("abort_proof_attempt", {
            "p_user_id": user_id,
            "p_task_id": task_id,
            "p_idempotency_key": idempotency_key,
        }).execute()

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
    def _active_plan_id_or_draft(self, user_id: str) -> str:
        """Aktif plan id — plan sayaç sorguları (list_plan_summaries) olmadan.

        Sohbet yolunda her mesaj başına özet+count sorgusu N+1'e dönüyordu.
        """
        plan_id = self._active_plan_id(user_id)
        if not plan_id:
            plan_id = self.create_draft_plan(user_id, name="Plan 1", slot_no=1)
        return plan_id

    # --- FAZ 7.6: Sohbet oturumları ---
    def _active_thread_id(self, user_id: str) -> Optional[str]:
        row = _maybe_single(
            self._db.table("users").select("active_thread_id").eq("id", user_id)
        )
        return row.get("active_thread_id") if row else None

    def _create_thread_row(self, user_id: str) -> str:
        plan_id = self._active_plan_id(user_id)
        thread_id = str(uuid.uuid4())
        self._db.table("chat_threads").insert({
            "id": thread_id,
            "user_id": user_id,
            "plan_id": plan_id,
        }).execute()
        self._db.table("users").update(
            {"active_thread_id": thread_id}
        ).eq("id", user_id).execute()
        return thread_id

    def _ensure_active_thread(self, user_id: str) -> Optional[str]:
        """FAZ 8 dayanıklılık: thread altyapısı hata verirse (ör. migration
        eksik) None döner — sohbet/plan akışı ASLA thread yüzünden ölmez;
        mesajlar plan bazlı eski davranışla yazılır."""
        try:
            thread_id = self._active_thread_id(user_id)
            if thread_id:
                return thread_id
            return self._create_thread_row(user_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Thread altyapısı devre dışı (degrade mod): %s", exc)
            return None

    def _touch_thread(self, user_id: str, thread_id: str, first_user_msg: str) -> None:
        row = _maybe_single(
            self._db.table("chat_threads").select("title")
            .eq("id", thread_id).eq("user_id", user_id)
        )
        payload: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if row is not None and not (row.get("title") or "").strip() and first_user_msg:
            payload["title"] = " ".join(first_user_msg.split())[:42].strip()
        self._db.table("chat_threads").update(payload).eq("id", thread_id).execute()

    def append_chat_message(self, user_id: str, message: ChatMessage) -> None:
        self.append_chat_messages(user_id, [message])

    def append_chat_messages(self, user_id: str, messages: list[ChatMessage]) -> None:
        """Tek istekte toplu ekleme: plan+oturum 1 kez çözülür, tek upsert atılır."""
        if not messages:
            return
        self._ensure_user(user_id)
        plan_id = self._active_plan_id_or_draft(user_id)
        thread_id = self._ensure_active_thread(user_id)
        upsert_rows: list[dict] = []
        insert_rows: list[dict] = []
        for message in messages:
            row = {
                "user_id": user_id,
                "client_message_id": message.id,
                "role": message.role,
                "content": message.content,
                "plan_id": plan_id,
            }
            if thread_id is not None:
                row["thread_id"] = thread_id
            (upsert_rows if message.id else insert_rows).append(row)
        if upsert_rows:
            self._db.table("chat_msgs").upsert(
                upsert_rows,
                on_conflict="user_id,client_message_id",
                ignore_duplicates=True,
            ).execute()
        if insert_rows:
            self._db.table("chat_msgs").insert(insert_rows).execute()
        if thread_id is not None:
            try:
                first_user = next((m.content for m in messages if m.role == "user"), "")
                self._touch_thread(user_id, thread_id, first_user)
            except Exception as exc:  # noqa: BLE001 — başlık güncellenemedi diye sohbet düşmez
                log.warning("Thread başlığı güncellenemedi: %s", exc)

    def list_chat_threads(self, user_id: str) -> list[ChatThread]:
        active_id = self._active_thread_id(user_id)
        rows = (
            self._db.table("chat_threads").select("id,title,updated_at")
            .eq("user_id", user_id).order("updated_at", desc=True).limit(50)
            .execute().data
        )
        return [
            ChatThread(
                id=row["id"],
                title=row.get("title") or "",
                is_active=row["id"] == active_id,
                updated_at=row.get("updated_at") or datetime.now(timezone.utc),
            )
            for row in rows
        ]

    def set_active_thread_title(self, user_id: str, title: str) -> None:
        # faz8.13/1b degrade modu: başlık güncellemesi sohbeti asla düşürmez.
        cleaned = " ".join(title.split()).strip()
        if not cleaned:
            return
        try:
            thread_id = self._active_thread_id(user_id)
            if not thread_id:
                return
            self._db.table("chat_threads").update(
                {"title": cleaned[:80]}
            ).eq("id", thread_id).eq("user_id", user_id).execute()
        except Exception as exc:  # noqa: BLE001
            log.warning("Thread başlığı yazılamadı (yoksayıldı): %s", exc)

    def create_chat_thread(self, user_id: str) -> ChatThread:
        self._ensure_user(user_id)
        thread_id = self._create_thread_row(user_id)
        return ChatThread(
            id=thread_id, title="", is_active=True,
            updated_at=datetime.now(timezone.utc),
        )

    def activate_chat_thread(self, user_id: str, thread_id: str) -> bool:
        row = _maybe_single(
            self._db.table("chat_threads").select("id,plan_id")
            .eq("id", thread_id).eq("user_id", user_id)
        )
        if not row:
            return False
        self._db.table("users").update(
            {"active_thread_id": thread_id}
        ).eq("id", user_id).execute()
        # Oturum bir plana bağlıysa bağlam bütünlüğü için o planı da aktive et.
        if row.get("plan_id"):
            self._db.table("users").update(
                {"active_plan_id": row["plan_id"]}
            ).eq("id", user_id).execute()
        return True

    def get_chat_history(self, user_id: str) -> list[ChatMessage]:
        # FAZ 8 dayanıklılık: thread altyapısı yoksa plan bazlı eski davranışa dön.
        try:
            thread_id = self._active_thread_id(user_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Thread okunamadı, plan bazlı geçmişe düşülüyor: %s", exc)
            thread_id = None
        if thread_id:
            query = (
                self._db.table("chat_msgs").select("id,client_message_id,role,content")
                .eq("user_id", user_id).eq("thread_id", thread_id)
            )
        else:
            plan_id = self._active_plan_id(user_id)
            if not plan_id:
                return []
            query = (
                self._db.table("chat_msgs").select("id,client_message_id,role,content")
                .eq("user_id", user_id).eq("plan_id", plan_id)
            )
        rows = (
            # Toplu insert'te created_at aynı olabilir; id ikincil anahtar
            # sıralamayı deterministik yapar.
            query.order("created_at").order("id").execute().data
        )
        return [
            ChatMessage(
                id=row.get("client_message_id") or f"legacy-{row['id']}",
                role=row["role"],
                content=row["content"],
            )
            for row in rows
        ]

    def clear_chat_history(self, user_id: str) -> int:
        """Aktif OTURUMUN mesajlarını sil (diğer oturumlar/plan/puan korunur)."""
        thread_id = self._active_thread_id(user_id)
        if not thread_id:
            return 0
        response = (
            self._db.table("chat_msgs").delete(count="exact")
            .eq("user_id", user_id).eq("thread_id", thread_id).execute()
        )
        self._db.table("chat_threads").update({"title": None}).eq("id", thread_id).execute()
        return int(response.count or 0)

    def save_intent(
        self,
        user_id: str,
        collected: CollectedIntent,
        duration_days: int,
        ready_for_plan: bool = False,
    ) -> None:
        self._ensure_user(user_id)
        plan_id = self._active_plan_id_or_draft(user_id)
        payload = json.dumps({
            "collected": collected.model_dump(mode="json"),
            "ready_for_plan": ready_for_plan,
        }, ensure_ascii=False)
        active = _maybe_single(
            self._db.table("intents").select("id").eq("user_id", user_id)
            .eq("plan_id", plan_id).eq("status", "active")
            .order("created_at", desc=True).limit(1)
        )
        values = {
            "text": payload,
            "duration_days": duration_days,
            "plan_id": plan_id,
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
        plan_id = self._active_plan_id(user_id)
        if not plan_id:
            return None
        active = _maybe_single(
            self._db.table("intents").select("text").eq("user_id", user_id)
            .eq("plan_id", plan_id).eq("status", "active")
            .order("created_at", desc=True).limit(1)
        )
        if not active:
            return None
        payload = parse_json_object(active.get("text"))
        try:
            return (
                CollectedIntent(**payload.get("collected", {})),
                bool(payload.get("ready_for_plan", False)),
            )
        except (TypeError, ValueError):
            return CollectedIntent(), False

    def get_latest_intent(self, user_id: str) -> CollectedIntent | None:
        plan_id = self._active_plan_id(user_id)
        if not plan_id:
            return None
        row = _maybe_single(
            self._db.table("intents").select("text").eq("user_id", user_id)
            .eq("plan_id", plan_id)
            .order("created_at", desc=True).limit(1)
        )
        if not row:
            return None
        payload = parse_json_object(row.get("text"))
        try:
            return CollectedIntent(**payload.get("collected", {}))
        except (TypeError, ValueError):
            return CollectedIntent()

    def complete_active_intent(self, user_id: str) -> None:
        plan_id = self._active_plan_id(user_id)
        if not plan_id:
            return
        self._db.table("intents").update({"status": "done"}).eq(
            "user_id", user_id
        ).eq("plan_id", plan_id).eq("status", "active").execute()

    # ------------------------------------------------------------------
    # Profil / hesap yaşam döngüsü (Faz 2)
    # ------------------------------------------------------------------
    def get_profile(self, user_id: str) -> UserProfile:
        self._ensure_user(user_id)
        row = self._db.table("users").select(
            "name,birth_date,zodiac_sign,gender,timezone,preferred_language,"
            "notif_hour,notif_minute,irade_modu_active,kvkk_consent_at"
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
            "gender": profile.gender,
            "timezone": profile.timezone,
            "preferred_language": profile.preferred_language,
            "notif_hour": profile.notif_hour,
            "notif_minute": profile.notif_minute,
            "irade_modu_active": profile.irade_modu_active,
            "kvkk_consent_at": (
                profile.kvkk_consent_at.isoformat()
                if profile.kvkk_consent_at else None
            ),
        }).eq("id", user_id).execute()

    def get_consents(self, user_id: str) -> list[ConsentRecord]:
        self._ensure_user(user_id)
        rows = (
            self._db.table("user_consents").select(
                "consent_kind,version,accepted,decided_at"
            ).eq("user_id", user_id).execute().data
        )
        return [
            ConsentRecord(
                kind=row["consent_kind"],
                version=row["version"],
                accepted=row["accepted"],
                decided_at=row["decided_at"],
            )
            for row in rows
        ]

    def save_consent(self, user_id: str, consent: ConsentRecord) -> None:
        self._ensure_user(user_id)
        self._db.table("user_consents").upsert({
            "user_id": user_id,
            "consent_kind": consent.kind,
            "version": consent.version,
            "accepted": consent.accepted,
            "decided_at": consent.decided_at.isoformat(),
        }, on_conflict="user_id,consent_kind,version").execute()

    def upsert_push_token(self, token: PushTokenRecord) -> None:
        self._ensure_user(token.user_id)
        self._db.table("push_tokens").upsert({
            "user_id": token.user_id,
            "token": token.token,
            "platform": token.platform,
            "enabled": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="token").execute()

    def disable_push_token(self, user_id: str, token: str) -> None:
        self._db.table("push_tokens").update({
            "enabled": False,
        }).eq("user_id", user_id).eq("token", token).execute()

    def list_notification_recipients(self) -> list[NotificationRecipient]:
        # PostgREST varsayılanı 1000 satırda keser — sayfalamadan 1000+
        # kullanıcıda bildirimler sessizce kaybolurdu (list_cron_users ile aynı desen).
        rows: list[dict] = []
        page_size = 1000
        while True:
            page = (
                self._db.table("push_tokens").select(
                    "user_id,token,last_task_reminder_date,last_bonus_offer_date,"
                    "last_tarot_push_date,last_recap_push_date,"
                    "users!inner(timezone,notif_hour,notif_minute)"
                ).eq("enabled", True)
                .range(len(rows), len(rows) + page_size - 1)
                .execute().data
            )
            rows.extend(page)
            if len(page) < page_size:
                break
        return [
            NotificationRecipient(
                user_id=row["user_id"],
                token=row["token"],
                last_task_reminder_date=_parse_optional_date(
                    row.get("last_task_reminder_date")
                ),
                last_bonus_offer_date=_parse_optional_date(
                    row.get("last_bonus_offer_date")
                ),
                last_tarot_push_date=_parse_optional_date(
                    row.get("last_tarot_push_date")
                ),
                last_recap_push_date=_parse_optional_date(
                    row.get("last_recap_push_date")
                ),
                timezone=(row.get("users") or {}).get("timezone") or "Europe/Istanbul",
                notif_hour=(row.get("users") or {}).get("notif_hour") or 8,
                notif_minute=(row.get("users") or {}).get("notif_minute") or 0,
            )
            for row in rows
        ]

    def mark_task_reminder_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        self._db.table("push_tokens").update({
            "last_task_reminder_date": day.isoformat(),
        }).eq("user_id", user_id).eq("token", token).execute()

    def mark_bonus_offer_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        self._db.table("push_tokens").update({
            "last_bonus_offer_date": day.isoformat(),
        }).eq("user_id", user_id).eq("token", token).execute()

    def mark_tarot_push_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        self._db.table("push_tokens").update({
            "last_tarot_push_date": day.isoformat(),
        }).eq("user_id", user_id).eq("token", token).execute()

    def mark_recap_push_sent(
        self, user_id: str, token: str, day: dt_date
    ) -> None:
        self._db.table("push_tokens").update({
            "last_recap_push_date": day.isoformat(),
        }).eq("user_id", user_id).eq("token", token).execute()

    def get_bonus_for_day(self, user_id: str, day: dt_date) -> BonusOffer | None:
        row = _maybe_single(
            self._db.table("bonus_offers").select("*")
            .eq("user_id", user_id).eq("day", day.isoformat())
        )
        return _bonus_from_row(row) if row else None

    def get_active_bonus(self, user_id: str) -> BonusOffer | None:
        rows = (
            self._db.table("bonus_offers").select("*")
            .eq("user_id", user_id).eq("status", "offered")
            .order("offered_at", desc=True).limit(1).execute().data
        )
        return _bonus_from_row(rows[0]) if rows else None

    def save_bonus_offer(self, offer: BonusOffer) -> BonusOffer:
        self._ensure_user(offer.user_id)
        row = self._db.table("bonus_offers").upsert({
            "id": offer.id,
            "user_id": offer.user_id,
            "bonus_key": offer.bonus_key,
            "title": offer.title,
            "tiny_instruction": offer.tiny_instruction,
            "category": offer.category,
            "day": offer.day.isoformat(),
            "status": offer.status,
            "offered_at": offer.offered_at.isoformat(),
        }, on_conflict="user_id,day").execute().data
        return _bonus_from_row(row[0]) if row else (
            self.get_bonus_for_day(offer.user_id, offer.day) or offer
        )

    def claim_bonus_completion(
        self, user_id: str, offer_id: str, completion_id: str
    ) -> bool:
        result = self._db.rpc("complete_bonus_offer", {
            "p_user_id": user_id,
            "p_offer_id": offer_id,
            "p_completion_id": completion_id,
        }).execute().data
        return bool(result)

    def get_subscription_row(self, user_id: str) -> dict:
        self._ensure_user(user_id)
        row = self._db.table("users").select(
            "subscription_status,trial_started_at,timezone"
        ).eq("id", user_id).single().execute().data
        payload = dict(row or {})
        payload["trial_started_at"] = coerce_datetime(payload.get("trial_started_at"))
        return payload

    def update_subscription(
        self,
        user_id: str,
        *,
        subscription_status: str | None = None,
        trial_started_at: datetime | None = None,
    ) -> None:
        self._ensure_user(user_id)
        payload: dict = {}
        if subscription_status is not None:
            payload["subscription_status"] = subscription_status
        if trial_started_at is not None:
            payload["trial_started_at"] = trial_started_at.isoformat()
        if payload:
            self._db.table("users").update(payload).eq("id", user_id).execute()

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

    # ------------------------------------------------------------------
    # V2: Fal modülü (FAZ 7) — fortune_log (MASTER_PLAN §2)
    # ------------------------------------------------------------------
    def save_fortune(self, user_id: str, record: FortuneRecord) -> None:
        self._ensure_user(user_id)
        self._db.table("fortune_log").insert({
            "id": record.id,
            "user_id": user_id,
            "type": record.type,
            "day": record.day.isoformat(),
            "result_json": json.dumps(record.result, ensure_ascii=False),
        }).execute()

    def count_fortunes_for_day(
        self, user_id: str, fortune_type: str, day: dt_date
    ) -> int:
        response = (
            self._db.table("fortune_log").select("id", count="exact")
            .eq("user_id", user_id).eq("type", fortune_type)
            .eq("day", day.isoformat()).limit(1).execute()
        )
        return int(response.count or 0)

    def get_fortune_for_day(
        self, user_id: str, fortune_type: str, day: dt_date
    ) -> Optional[FortuneRecord]:
        row = _maybe_single(
            self._db.table("fortune_log")
            .select("id,type,day,result_json,created_at")
            .eq("user_id", user_id).eq("type", fortune_type)
            .eq("day", day.isoformat())
            .order("created_at", desc=True).limit(1)
        )
        if not row:
            return None
        return _fortune_from_row(row)

    # ------------------------------------------------------------------
    # İdol Modu persona deposu (Dalga 4.3) — yeni idol = deploy YOK
    # ------------------------------------------------------------------
    def list_idol_personas(self) -> list[dict]:
        rows = (
            self._db.table("idol_personas")
            .select("slug,path_name,tagline,category,inspired_by,source_note,dossier,tags")
            .eq("is_active", True).order("path_name").execute().data
        )
        personas: list[dict] = []
        for row in rows:
            dossier = row.get("dossier")
            if not isinstance(dossier, dict):
                dossier = parse_json_object(dossier)
            personas.append({**row, "dossier": dossier or {}})
        return personas

    def upsert_idol_persona(self, persona: dict, chunks: list[dict]) -> None:
        row = {
            "slug": persona["slug"],
            "path_name": persona["path_name"],
            "tagline": persona.get("tagline", ""),
            "category": persona.get("category", "genel"),
            "inspired_by": persona.get("inspired_by", ""),
            "source_note": persona.get("source_note", ""),
            "dossier": persona.get("dossier", {}),
            "tags": persona.get("tags", []),
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._db.table("idol_personas").upsert(row, on_conflict="slug").execute()
        saved = _maybe_single(
            self._db.table("idol_personas").select("id").eq("slug", persona["slug"])
        )
        if not saved:
            return
        persona_id = saved["id"]
        # Chunk'lar tam yenilenir (dossier güncellenince eski parçalar kalmasın).
        self._db.table("persona_chunks").delete().eq("persona_id", persona_id).execute()
        if chunks:
            self._db.table("persona_chunks").insert([
                {
                    "persona_id": persona_id,
                    "section": chunk["section"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                }
                for chunk in chunks
            ]).execute()

    # --- faz8.13/4: Online rekabet (opt-in takma adlı lig) ---
    # Tablo: league_members(user_id, alias, score, streak, updated_at) —
    # RUN_IN_SUPABASE_SQL_EDITOR.sql'de. KVKK: yalnız rumuz + sayı tutulur.
    def league_get_member(self, user_id: str) -> Optional[dict]:
        row = _maybe_single(
            self._db.table("league_members")
            .select("alias,score,streak")
            .eq("user_id", user_id).limit(1)
        )
        return dict(row) if row else None

    def league_upsert_member(
        self, user_id: str, alias: str, score: int, streak: int
    ) -> None:
        self._db.table("league_members").upsert({
            "user_id": user_id,
            "alias": alias,
            "score": score,
            "streak": streak,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id").execute()

    def league_remove_member(self, user_id: str) -> None:
        self._db.table("league_members").delete().eq("user_id", user_id).execute()

    def league_top(self, limit: int = 50) -> list[dict]:
        rows = (
            self._db.table("league_members")
            .select("user_id,alias,score,streak")
            .order("score", desc=True).order("streak", desc=True)
            .limit(limit)
            .execute().data
        )
        return [dict(row) for row in rows]

    def list_fortunes(self, user_id: str, limit: int = 50) -> list[FortuneRecord]:
        rows = (
            self._db.table("fortune_log")
            .select("id,type,day,result_json,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True).limit(limit)
            .execute().data
        )
        records: list[FortuneRecord] = []
        for row in rows:
            try:
                records.append(_fortune_from_row(row))
            except Exception:  # noqa: BLE001 — bozuk satır tüm geçmişi düşürmesin
                log.warning("fortune_log satırı okunamadı (yoksayıldı)", extra={"id": row.get("id")})
        return records

"""
Niyetsen — Supabase Depolama Katmanı (Faz 2 yuvası)
Repository arayüzünün gerçek DB implementasyonu. Tablolar: NIYETSEN_MASTER_PLAN §2
(users, streaks, points, plans, tasks — migration: niyetsen_core_tables).
service_role anahtarıyla çalışır → RLS bypass edilir; erişim kontrolü bu backend'in
üstünde (JWT middleware, api/routes.py > get_current_user).
"""
from __future__ import annotations

from typing import Optional

from supabase import Client, create_client

from app.config import CATEGORIES, settings
from app.models.schemas import GameState, Plan, PlanDay, Task
from app.storage.base import Repository


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
        duration_min=row["duration_min"],
        tiny_version=row["tiny_version"],
        status=row["status"],
        date=row["date"],
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
        self._db.table("tasks").update({
            "title": task.title,
            "task_type": task.task_type,
            "categories": task.categories,
            "image_keyword": task.image_keyword,
            "image_url": task.image_url,
            "duration_min": task.duration_min,
            "tiny_version": task.tiny_version,
            "status": task.status,
            "date": task.date.isoformat() if task.date else None,
        }).eq("id", task.id).execute()

    # ------------------------------------------------------------------
    # Kanıt denemeleri
    # ------------------------------------------------------------------
    def get_proof_attempts(self, user_id: str, task_id: str) -> int:
        row = _maybe_single(self._db.table("tasks").select("proof_attempts").eq("id", task_id))
        return (row or {}).get("proof_attempts", 0)

    def incr_proof_attempts(self, user_id: str, task_id: str) -> int:
        new_val = self.get_proof_attempts(user_id, task_id) + 1
        self._db.table("tasks").update({"proof_attempts": new_val}).eq("id", task_id).execute()
        return new_val

"""Niyetsen — çoklu plan projeleri (free=1 plan, abonelikle sınırsız yeni niyet)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.schemas import CollectedIntent, DailyTaskItem, DailyTasksResponse, PlanSummary
from app.services import plan_service, subscription_service
from app.storage.base import Repository


def _user_local_today(timezone_name: str) -> date:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Europe/Istanbul")
    return datetime.now(timezone.utc).astimezone(tz).date()


def list_projects(repo: Repository, user_id: str) -> list[PlanSummary]:
    return repo.list_plan_summaries(user_id)


def activate_project(repo: Repository, user_id: str, plan_id: str) -> PlanSummary:
    if not repo.plan_belongs_to_user(user_id, plan_id):
        raise ValueError("Plan bulunamadı.")
    repo.set_active_plan(user_id, plan_id)
    summaries = repo.list_plan_summaries(user_id)
    match = next((item for item in summaries if item.id == plan_id), None)
    if match is None:
        raise ValueError("Plan bulunamadı.")
    return match


def rename_project(
    repo: Repository, user_id: str, plan_id: str, name: str
) -> PlanSummary:
    if not repo.plan_belongs_to_user(user_id, plan_id):
        raise ValueError("Plan bulunamadı.")
    repo.rename_plan(user_id, plan_id, name.strip())
    summaries = repo.list_plan_summaries(user_id)
    match = next((item for item in summaries if item.id == plan_id), None)
    if match is None:
        raise ValueError("Plan bulunamadı.")
    return match


def start_new_project(repo: Repository, user_id: str) -> PlanSummary:
    if repo.count_completed_plans(user_id) >= 1:
        subscription_service.require_paid_subscription(repo, user_id)
    repo.complete_active_intent(user_id)
    slot_no = repo.next_plan_slot(user_id)
    plan_id = repo.create_draft_plan(user_id, name=f"Plan {slot_no}", slot_no=slot_no)
    repo.set_active_plan(user_id, plan_id)
    repo.save_intent(user_id, CollectedIntent(), 365, ready_for_plan=False)
    # Yeni niyet = yeni sohbet oturumu. Eski test yazıları aktif thread'de kalmasın.
    try:
        repo.create_chat_thread(user_id)
    except Exception:
        # Thread degrade: sohbet hatası yeni planı düşürmez (hafıza kuralı).
        pass
    summaries = repo.list_plan_summaries(user_id)
    match = next((item for item in summaries if item.id == plan_id), None)
    if match is None:
        raise ValueError("Yeni proje oluşturulamadı.")
    return match


def get_today_tasks(repo: Repository, user_id: str, *, today: date | None = None) -> list[DailyTaskItem]:
    if today is None:
        profile = repo.get_profile(user_id)
        current = _user_local_today(profile.timezone)
    else:
        current = today
    return repo.list_daily_tasks_for_date(user_id, current)


def get_daily_tasks_response(
    repo: Repository, user_id: str, *, today: date | None = None
) -> DailyTasksResponse:
    """Bugünün görevleri + parti geride kaldıysa needs_extension=True."""
    if today is None:
        profile = repo.get_profile(user_id)
        current = _user_local_today(profile.timezone)
    else:
        current = today
    items = repo.list_daily_tasks_for_date(user_id, current)
    plan = repo.get_plan(user_id)
    if plan is None or not plan.days:
        return DailyTasksResponse(items=items, has_active_plan=False)
    plan_day = (current - plan.start_date).days + 1
    needs = plan_service.needs_plan_extension(
        duration_days=plan.duration_days,
        batch_generated_until=plan.batch_generated_until,
        plan_day=plan_day,
    )
    return DailyTasksResponse(
        items=items,
        needs_extension=needs,
        plan_day=max(plan_day, 0),
        batch_generated_until=plan.batch_generated_until,
        active_plan_name=plan.name or "Planım",
        has_active_plan=True,
    )

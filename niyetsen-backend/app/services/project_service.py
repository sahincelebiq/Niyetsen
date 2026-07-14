"""Niyetsen — çoklu plan projeleri (free=1 plan, abonelikle sınırsız yeni niyet)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.schemas import CollectedIntent, DailyTaskItem, PlanSummary
from app.services import subscription_service
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

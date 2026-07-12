"""Niyetsen — deneme ve abonelik erişim kuralları (MASTER_PLAN §1.1, §1.7)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.schemas import SubscriptionInfo
from app.storage.base import Repository

SubscriptionStatus = Literal["free", "trial", "active", "expired", "cancelled"]

TRIAL_DAYS = 3
PREMIUM_STATUSES = frozenset({"trial", "active"})


def _user_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Europe/Istanbul")


def _local_today(timezone_name: str) -> date:
    return datetime.now(timezone.utc).astimezone(_user_timezone(timezone_name)).date()


def trial_days_remaining(
    trial_started_at: Optional[datetime],
    timezone_name: str,
    *,
    today: Optional[date] = None,
) -> int:
    if trial_started_at is None:
        return TRIAL_DAYS
    local_start = trial_started_at.astimezone(_user_timezone(timezone_name)).date()
    current = today or _local_today(timezone_name)
    elapsed = (current - local_start).days
    return max(0, TRIAL_DAYS - elapsed)


def trial_is_active(
    trial_started_at: Optional[datetime],
    timezone_name: str,
    *,
    today: Optional[date] = None,
) -> bool:
    if trial_started_at is None:
        return False
    return trial_days_remaining(trial_started_at, timezone_name, today=today) > 0


def build_subscription_info(
    *,
    status: str,
    trial_started_at: Optional[datetime],
    timezone_name: str,
    has_plan: bool,
    today: Optional[date] = None,
) -> SubscriptionInfo:
    normalized = status if status in {"free", "trial", "active", "expired", "cancelled"} else "free"
    days_left = trial_days_remaining(trial_started_at, timezone_name, today=today)

    if normalized == "active":
        has_access = True
        show_paywall = False
    elif normalized == "trial":
        active = trial_is_active(trial_started_at, timezone_name, today=today)
        has_access = active
        show_paywall = not active
        if not active:
            normalized = "expired"
    elif normalized == "free" and has_plan and trial_started_at is None:
        # Eski hesaplar: plan var ama deneme başlamamış — hemen denemeye al.
        has_access = True
        show_paywall = False
    elif normalized == "free":
        has_access = True
        show_paywall = False
    else:
        has_access = False
        show_paywall = True

    return SubscriptionInfo(
        status=normalized,
        trial_started_at=trial_started_at,
        trial_days_remaining=days_left if normalized in {"trial", "expired"} else 0,
        has_premium_access=has_access,
        show_paywall=show_paywall,
    )


def get_subscription(repo: Repository, user_id: str) -> SubscriptionInfo:
    row = repo.get_subscription_row(user_id)
    has_plan = repo.get_plan(user_id) is not None
    return build_subscription_info(
        status=row["subscription_status"],
        trial_started_at=row.get("trial_started_at"),
        timezone_name=row.get("timezone", "Europe/Istanbul"),
        has_plan=has_plan,
    )


def start_trial_if_needed(repo: Repository, user_id: str) -> None:
    row = repo.get_subscription_row(user_id)
    if row.get("trial_started_at") is not None:
        return
    now = datetime.now(timezone.utc)
    repo.update_subscription(
        user_id,
        subscription_status="trial",
        trial_started_at=now,
    )


def require_premium_access(repo: Repository, user_id: str) -> SubscriptionInfo:
    info = get_subscription(repo, user_id)
    if not info.has_premium_access:
        raise PermissionError("paywall")
    return info


def apply_revenuecat_event(
    repo: Repository,
    *,
    app_user_id: str,
    event_type: str,
    expiration_at: Optional[datetime] = None,
) -> SubscriptionInfo:
    active_events = {
        "INITIAL_PURCHASE",
        "RENEWAL",
        "UNCANCELLATION",
        "PRODUCT_CHANGE",
        "SUBSCRIPTION_EXTENDED",
    }
    inactive_events = {
        "CANCELLATION",
        "EXPIRATION",
        "BILLING_ISSUE",
    }

    if event_type in active_events:
        repo.update_subscription(app_user_id, subscription_status="active")
    elif event_type in inactive_events:
        row = repo.get_subscription_row(app_user_id)
        if trial_is_active(
            row.get("trial_started_at"),
            row.get("timezone", "Europe/Istanbul"),
        ):
            repo.update_subscription(app_user_id, subscription_status="trial")
        else:
            status = "cancelled" if event_type == "CANCELLATION" else "expired"
            repo.update_subscription(app_user_id, subscription_status=status)
    elif expiration_at and expiration_at > datetime.now(timezone.utc):
        repo.update_subscription(app_user_id, subscription_status="active")

    return get_subscription(repo, app_user_id)


def sync_expired_trials(repo: Repository, user_id: str) -> SubscriptionInfo:
    row = repo.get_subscription_row(user_id)
    if row["subscription_status"] != "trial":
        return get_subscription(repo, user_id)
    if trial_is_active(
        row.get("trial_started_at"),
        row.get("timezone", "Europe/Istanbul"),
    ):
        return get_subscription(repo, user_id)
    repo.update_subscription(user_id, subscription_status="expired")
    return get_subscription(repo, user_id)

"""FAZ 5 — deneme ve abonelik kuralları."""
from datetime import date, datetime, timezone

import pytest

from app.services import subscription_service
from app.storage.repository import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository()


def test_free_user_has_access_before_plan(repo: InMemoryRepository) -> None:
    info = subscription_service.get_subscription(repo, "user-1")
    assert info.status == "free"
    assert info.has_premium_access is True
    assert info.show_paywall is False


def test_first_plan_starts_trial(repo: InMemoryRepository) -> None:
    subscription_service.start_trial_if_needed(repo, "user-1")
    info = subscription_service.get_subscription(repo, "user-1")
    assert info.status == "trial"
    assert info.trial_days_remaining == 3
    assert info.has_premium_access is True


def test_trial_expires_after_three_days(repo: InMemoryRepository) -> None:
    started = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)
    repo.update_subscription(
        "user-1",
        subscription_status="trial",
        trial_started_at=started,
    )
    info = subscription_service.build_subscription_info(
        status="trial",
        trial_started_at=started,
        timezone_name="Europe/Istanbul",
        has_plan=True,
        today=date(2026, 7, 13),
    )
    assert info.has_premium_access is False
    assert info.show_paywall is True


def test_active_subscription_unlocks_access(repo: InMemoryRepository) -> None:
    repo.update_subscription("user-1", subscription_status="active")
    info = subscription_service.get_subscription(repo, "user-1")
    assert info.has_premium_access is True
    assert info.show_paywall is False


def test_revenuecat_initial_purchase_activates(repo: InMemoryRepository) -> None:
    subscription_service.start_trial_if_needed(repo, "user-1")
    info = subscription_service.apply_revenuecat_event(
        repo,
        app_user_id="user-1",
        event_type="INITIAL_PURCHASE",
    )
    assert info.status == "active"
    assert info.has_premium_access is True


def test_revenuecat_expiration_locks_after_trial(repo: InMemoryRepository) -> None:
    started = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    repo.update_subscription(
        "user-1",
        subscription_status="active",
        trial_started_at=started,
    )
    info = subscription_service.apply_revenuecat_event(
        repo,
        app_user_id="user-1",
        event_type="EXPIRATION",
    )
    assert info.status == "expired"
    assert info.has_premium_access is False


def test_sync_expired_trials_updates_status(repo: InMemoryRepository) -> None:
    started = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    repo.update_subscription(
        "user-1",
        subscription_status="trial",
        trial_started_at=started,
    )
    info = subscription_service.build_subscription_info(
        status="trial",
        trial_started_at=started,
        timezone_name="Europe/Istanbul",
        has_plan=True,
        today=date(2026, 7, 10),
    )
    assert info.show_paywall is True
    synced = subscription_service.sync_expired_trials(repo, "user-1")
    assert synced.status == "expired"

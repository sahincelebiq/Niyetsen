"""FAZ 5 — deneme ve abonelik kuralları."""
from datetime import date, datetime, timedelta, timezone

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
    assert info.trial_days_remaining == 7
    assert info.has_premium_access is True


def test_start_trial_does_not_downgrade_active_subscriber(repo: InMemoryRepository) -> None:
    """Abone ilk planını üretirken trial'a düşmemeli (çoklu niyet kilidi)."""
    repo.update_subscription("paid-user", subscription_status="active")
    subscription_service.start_trial_if_needed(repo, "paid-user")
    row = repo.get_subscription_row("paid-user")
    assert row["subscription_status"] == "active"
    assert row.get("trial_started_at") is None
    info = subscription_service.get_subscription(repo, "paid-user")
    assert info.status == "active"
    assert info.has_premium_access is True


def test_trial_expires_after_seven_days(repo: InMemoryRepository) -> None:
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
        today=date(2026, 7, 17),
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


def test_cancellation_keeps_access_until_expiration(repo: InMemoryRepository) -> None:
    # Sabit takvim tarihi değil — "şimdi"ye göre gelecek (flaky önlemi).
    expires = datetime.now(timezone.utc) + timedelta(days=14)
    repo.update_subscription("user-1", subscription_status="active")
    info = subscription_service.apply_revenuecat_event(
        repo,
        app_user_id="user-1",
        event_type="CANCELLATION",
        expiration_at=expires,
    )
    assert info.status == "active"
    assert info.has_premium_access is True


def test_cancellation_after_expiration_locks_access(repo: InMemoryRepository) -> None:
    expires = datetime.now(timezone.utc) - timedelta(days=14)
    repo.update_subscription("user-1", subscription_status="active")
    info = subscription_service.apply_revenuecat_event(
        repo,
        app_user_id="user-1",
        event_type="CANCELLATION",
        expiration_at=expires,
    )
    assert info.status == "cancelled"
    assert info.has_premium_access is False


def test_trial_started_at_iso_string_does_not_500(repo: InMemoryRepository) -> None:
    """Canlı 500: PostgREST trial_started_at'i str verir; .astimezone patlıyordu."""
    repo.update_subscription("user-str", subscription_status="trial")
    row = repo.get_subscription_row("user-str")
    row["trial_started_at"] = "2026-08-10T08:00:00+00:00"
    info = subscription_service.get_subscription(repo, "user-str")
    assert info.status in {"trial", "expired"}
    assert info.trial_days_remaining >= 0


def test_trial_started_at_z_suffix_and_naive_datetime(repo: InMemoryRepository) -> None:
    repo.update_subscription("user-z", subscription_status="trial")
    row = repo.get_subscription_row("user-z")
    row["trial_started_at"] = "2026-08-12T08:00:00Z"
    info = subscription_service.build_subscription_info(
        status="trial",
        trial_started_at=row["trial_started_at"],
        timezone_name="Europe/Istanbul",
        has_plan=True,
        today=date(2026, 8, 13),
    )
    assert info.trial_days_remaining == 6
    naive = datetime(2026, 8, 10, 8, 0)
    remaining = subscription_service.trial_days_remaining(
        naive, "Europe/Istanbul", today=date(2026, 8, 13)
    )
    assert remaining == 4


def test_subscription_http_survives_iso_string_trial(isolated_in_memory_repo) -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    user = "http-str-trial"
    isolated_in_memory_repo.update_subscription(user, subscription_status="trial")
    isolated_in_memory_repo.get_subscription_row(user)["trial_started_at"] = (
        "2026-08-11T06:00:00Z"
    )
    res = TestClient(app).get("/me/subscription", headers={"X-User-Id": user})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"trial", "expired"}
    assert "trial_days_remaining" in body

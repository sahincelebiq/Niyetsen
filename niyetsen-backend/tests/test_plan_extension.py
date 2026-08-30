"""Plan partisi: geçmiş gün uydurma yok, bugünden atla + prefetch."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Plan, PlanDay, Task, UserProfile
from app.services import plan_service
from app.storage.repository import repo

client = TestClient(app)

FAKE_PLAN_JSON = {
    "days": [
        {
            "day": 1,
            "theme": "Atlama haftası",
            "tasks": [
                {
                    "title": "Kampüste 20 dakika yürü",
                    "task_type": "yer",
                    "categories": ["İstikrar"],
                    "image_keyword": "campus walk",
                    "duration_min": 20,
                    "tiny_version": "Kapıdan çık.",
                }
            ],
        }
    ]
}


def test_next_generation_start_day_jumps_and_prefetches() -> None:
    assert plan_service.next_generation_start_day(
        duration_days=180, batch_generated_until=7, plan_day=40
    ) == 40
    assert plan_service.next_generation_start_day(
        duration_days=180, batch_generated_until=7, plan_day=7
    ) == 8
    assert plan_service.next_generation_start_day(
        duration_days=180, batch_generated_until=7, plan_day=6
    ) == 8
    assert plan_service.next_generation_start_day(
        duration_days=180, batch_generated_until=7, plan_day=5
    ) is None
    assert plan_service.next_generation_start_day(
        duration_days=7, batch_generated_until=7, plan_day=7
    ) is None


def test_ensure_today_skips_past_days_and_lands_on_today(monkeypatch) -> None:
    async def fake_generate_json(*args, **kwargs):
        return FAKE_PLAN_JSON

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)

    user_id = "jump-day-40"
    today = date(2026, 8, 30)
    start = today - timedelta(days=39)  # plan günü 40
    repo.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    repo.save_plan(
        user_id,
        Plan(
            id="old-batch",
            duration_days=180,
            batch_generated_until=7,
            start_date=start,
            days=[
                PlanDay(
                    day=1,
                    theme="İlk hafta",
                    tasks=[
                        Task(
                            id="d1",
                            day=1,
                            date=start,
                            title="Eski görev",
                            categories=["İrade"],
                        )
                    ],
                )
            ],
            name="180 gün",
        ),
    )
    monkeypatch.setattr(
        "app.api.routes._user_today",
        lambda _tz: today,
    )

    resp = client.post("/plan/ensure-today", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_generated_until"] >= 40
    new_dates = [
        date.fromisoformat(task["date"])
        for day in body["days"]
        for task in day["tasks"]
        if task["id"] != "d1"
    ]
    assert new_dates
    assert all(day >= today for day in new_dates)
    assert not any(8 <= day["day"] <= 39 for day in body["days"])


def test_ensure_today_works_without_premium(monkeypatch) -> None:
    async def fake_generate_json(*args, **kwargs):
        return FAKE_PLAN_JSON

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)
    user_id = "free-extend"
    today = date(2026, 8, 30)
    start = today - timedelta(days=10)
    repo.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    repo.update_subscription(
        user_id,
        subscription_status="expired",
        trial_started_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    repo.save_plan(
        user_id,
        Plan(
            id="free-plan",
            duration_days=180,
            batch_generated_until=7,
            start_date=start,
            days=[PlanDay(day=1, tasks=[])],
        ),
    )
    monkeypatch.setattr("app.api.routes._user_today", lambda _tz: today)
    resp = client.post("/plan/ensure-today", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    assert resp.json()["batch_generated_until"] >= 11


def test_ensure_today_race_does_not_duplicate_days(monkeypatch) -> None:
    """Release QA T2: Bugün + Planım aynı anda uzatınca kopya gün oluşmaz.

    Senaryo: istek start_day'i hesapladıktan sonra (ama kaydetmeden önce)
    rakip istek aynı günleri kaydetmiş olsun — merge var olan günleri atlar.
    """
    async def fake_generate_json(*args, **kwargs):
        return FAKE_PLAN_JSON

    monkeypatch.setattr(plan_service, "generate_json", fake_generate_json)
    user_id = "race-user"
    today = date(2026, 8, 30)
    start = today - timedelta(days=39)  # plan günü 40
    repo.save_profile(user_id, UserProfile(timezone="Europe/Istanbul"))
    rival_day = PlanDay(
        day=40,
        theme="Rakip istek",
        tasks=[Task(
            id="rival-40", day=40, date=today,
            title="Rakip görev", categories=["İrade"],
        )],
    )
    plan = Plan(
        id="race-plan",
        duration_days=180,
        batch_generated_until=7,   # start_day hesabı hâlâ 40 der
        start_date=start,
        days=[PlanDay(day=1, tasks=[]), rival_day],  # 40 zaten kayıtlı
    )
    repo.save_plan(user_id, plan)
    monkeypatch.setattr("app.api.routes._user_today", lambda _tz: today)

    resp = client.post("/plan/ensure-today", headers={"X-User-Id": user_id})
    assert resp.status_code == 200
    body = resp.json()
    day_numbers = [d["day"] for d in body["days"]]
    assert day_numbers.count(40) == 1  # kopya gün yok
    day40 = next(d for d in body["days"] if d["day"] == 40)
    assert any(t["id"] == "rival-40" for t in day40["tasks"])  # rakip korunur


def test_daily_prefetch_flag_on_penultimate_day() -> None:
    from app.services import project_service

    user_id = "prefetch-flag"
    start = date(2026, 8, 24)
    today = start + timedelta(days=5)  # gün 6 / batch 7
    repo.save_plan(
        user_id,
        Plan(
            id="pre",
            duration_days=180,
            batch_generated_until=7,
            start_date=start,
            days=[PlanDay(day=1, tasks=[])],
        ),
    )
    resp = project_service.get_daily_tasks_response(repo, user_id, today=today)
    assert resp.needs_extension is True
    assert resp.plan_day == 6

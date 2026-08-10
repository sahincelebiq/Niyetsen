"""FAZ 8.8 — Niyetsen Raporu ('Wrapped') testleri."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import GameState, Plan, PlanDay, Task
from app.services import recap_service
from app.storage.repository import repo

client = TestClient(app)
HEADERS = {"X-User-Id": "recap-user"}


def _grant_pro() -> None:
    repo.update_subscription("recap-user", subscription_status="active")


def _plan_with_done_tasks(n_done: int) -> Plan:
    today = date.today()
    start = today - timedelta(days=9)
    days = []
    for i in range(10):
        task_date = start + timedelta(days=i)
        days.append(PlanDay(day=i + 1, tasks=[Task(
            id=f"t{i}",
            day=i + 1,
            title=f"Görev {i}",
            categories=["Disiplin"],
            status="done" if i < n_done else "pending",
            date=task_date,
        )]))
    return Plan(
        id="p1", duration_days=10, batch_generated_until=10,
        start_date=start, days=days,
    )


def test_build_recap_counts_done_tasks_and_orders_cards():
    state = GameState(user_id="u", streak_len=3, best_streak=7)
    state.points["Disiplin"] = 350
    recap = recap_service.build_recap(
        state=state, plan=_plan_with_done_tasks(4), user_name="Şahin",
    )
    assert recap.completed_tasks == 4
    assert recap.top_category == "Disiplin"
    assert [c.kind for c in recap.cards] == [
        "intro", "journey", "tasks", "trait", "streak", "closing",
    ]
    assert "Şahin" in recap.cards[0].title
    assert "4 görev" in recap.cards[2].headline


def test_build_recap_without_plan_is_safe():
    recap = recap_service.build_recap(
        state=GameState(user_id="u"), plan=None,
    )
    assert recap.completed_tasks == 0
    assert len(recap.cards) == 6  # kartlar her durumda dolu — boş story yok


def test_recap_endpoint_returns_cards():
    _grant_pro()
    response = client.get("/me/recap", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "14d"
    assert len(body["cards"]) == 6


def test_recap_endpoint_invalid_period_falls_back():
    _grant_pro()
    response = client.get("/me/recap?period=99y", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["period"] == "14d"


def test_recap_endpoint_free_user_gets_paywall():
    repo.update_subscription("recap-free", subscription_status="free")
    response = client.get("/me/recap", headers={"X-User-Id": "recap-free"})
    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "paywall_required"


def test_is_recap_push_due_schedule():
    assert not recap_service.is_recap_push_due(13)
    assert recap_service.is_recap_push_due(14)
    assert not recap_service.is_recap_push_due(15)
    assert not recap_service.is_recap_push_due(43)
    assert recap_service.is_recap_push_due(44)
    assert recap_service.recap_push_period_days(14) == 14
    assert recap_service.recap_push_period_days(44) == 30


def test_build_recap_aggregates_all_plans_and_period_trait():
    """FAZ 8.9: çoklu plan gerçek veri — iki planın görevleri toplanır,
    dönem kategorisi fiilen işlenen görevlerden çıkar."""
    today = date.today()

    def plan_with(cat: str, n_done: int, pid: str, start_offset: int) -> Plan:
        start = today - timedelta(days=start_offset)
        days = [
            PlanDay(day=i + 1, tasks=[Task(
                id=f"{pid}-t{i}", day=i + 1, title=f"{cat} görevi {i}",
                categories=[cat],
                status="done" if i < n_done else "pending",
                date=start + timedelta(days=i),
                proof_id="p1" if i == 0 else None,
            )])
            for i in range(5)
        ]
        return Plan(id=pid, duration_days=5, batch_generated_until=5,
                    start_date=start, days=days)

    plan_a = plan_with("Disiplin", 3, "pa", 4)   # 3 done
    plan_b = plan_with("Sosyallik", 2, "pb", 20)  # start 20 gün önce, 2 done (dönem dışı)
    recap = recap_service.build_recap(
        state=GameState(user_id="u"),
        plan=plan_a,
        plans=[plan_a, plan_b],
        period="14d",
        today=today,
    )
    assert recap.days_in == 21  # yolculuk EN ESKİ plandan sayılır
    assert recap.completed_tasks == 3  # dönem içi: yalnız plan_a'nın 3'ü
    trait = next(c for c in recap.cards if c.kind == "trait")
    assert trait.headline == "Disiplin"  # dönem-gerçek kategori
    tasks_card = next(c for c in recap.cards if c.kind == "tasks")
    assert "kanıtla" in tasks_card.subtitle  # proof_id sayıldı
    intro = next(c for c in recap.cards if c.kind == "intro")
    assert "2 niyeti" in intro.subtitle

def test_dashboard_kpis_all_time():
    """faz8.13/3: dashboard ilk günden bugüne gerçek KPI'ları taşır."""
    state = GameState(user_id="u", streak_len=2, best_streak=5)
    state.points["Disiplin"] = 200
    recap = recap_service.build_recap(
        state=state, plan=_plan_with_done_tasks(4),
    )
    dash = recap.dashboard
    assert dash is not None
    assert dash.total_tasks == 10
    assert dash.completed_tasks == 4
    assert dash.completion_rate == 40
    assert dash.category_counts["Disiplin"] == 4
    assert dash.best_streak == 5
    assert dash.plans_count == 1
    assert len(dash.weekly_completed) == 8
    assert sum(dash.weekly_completed) == 4

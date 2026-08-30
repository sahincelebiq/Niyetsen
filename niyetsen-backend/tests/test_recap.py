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


def test_recap_endpoint_free_user_gets_dashboard_not_story():
    """Kapı içeride: panel + ayna ücretsiz; hikâye kartları PRO."""
    repo.update_subscription("recap-free", subscription_status="free")
    response = client.get("/me/recap", headers={"X-User-Id": "recap-free"})
    assert response.status_code == 200
    body = response.json()
    assert body["cards"] == []
    assert body["dashboard"] is not None
    assert "mirror_line" in body["dashboard"]


def test_mirror_line_is_honest_not_shaming():
    today = date.today()
    start = today - timedelta(days=4)
    state = GameState(user_id="u", streak_len=2, best_streak=4)
    state.points["Disiplin"] = 200
    for cat in ("İrade", "İstikrar", "Özgüven", "Sosyallik"):
        state.points[cat] = 40
    state.points["Özsaygı"] = 0
    plan = Plan(
        id="p-mirror", duration_days=5, batch_generated_until=5,
        start_date=start, days=[
            PlanDay(day=1, tasks=[Task(
                id="d1", day=1, title="Koşu", categories=["Disiplin"],
                status="done", date=start,
            )]),
            PlanDay(day=2, tasks=[Task(
                id="s1", day=2, title="Sessiz", categories=["Özsaygı"],
                status="missed_silent", date=start + timedelta(days=1),
            )]),
        ],
    )
    recap = recap_service.build_recap(state=state, plan=plan, period="7d")
    line = recap.dashboard.mirror_line if recap.dashboard else ""
    assert "Disiplin" in line
    assert "Özsaygı" in line
    assert "sessiz" in line.lower()
    assert "kaçırdın" not in line.lower()
    assert "ceza" not in line.lower()

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

def test_dashboard_patterns_hours_and_bonus_insights():
    """Release QA T8: gün/saat örüntüsü + bonus sayıları + dürüst içgörüler.
    Story kartlarında kaçırılan yine GÖSTERİLMEZ (Wrapped kilidi)."""
    from datetime import datetime, timezone

    from app.models.schemas import PointLogRecord

    today = date(2026, 8, 26)  # Çarşamba
    monday = today - timedelta(days=2)
    plan = Plan(
        id="p-pattern", duration_days=7, batch_generated_until=7,
        start_date=monday, days=[
            PlanDay(day=1, tasks=[Task(
                id="pd1", day=1, title="Pazartesi görevi",
                categories=["Disiplin"], status="done", date=monday,
            )]),
            PlanDay(day=2, tasks=[Task(
                id="pm1", day=2, title="Salı görevi",
                categories=["İrade"], status="missed_silent",
                date=monday + timedelta(days=1),
            )]),
        ],
    )
    state = GameState(user_id="u")
    state.points["Disiplin"] = 150
    # 18:30 UTC = 21:30 İstanbul → saat kovası 21. Üç kayıt: içgörü eşiği ≥3.
    log_entries = [
        PointLogRecord(
            user_id="u", category="Disiplin", delta=50,
            reason="görev tamamlandı",
            created_at=datetime(2026, 8, 20 + i, 18, 30, tzinfo=timezone.utc),
        )
        for i in range(3)
    ]
    recap = recap_service.build_recap(
        state=state, plan=plan, period="7d", today=today,
        point_log=log_entries,
        timezone_name="Europe/Istanbul",
        bonus_counts=(4, 2),
    )
    dash = recap.dashboard
    assert dash is not None
    assert dash.weekday_done[0] == 1          # Pazartesi tamamlanan
    assert dash.weekday_missed[1] == 1        # Salı sessiz kaçırma
    assert dash.hour_done[21] == 3            # İstanbul saatiyle 21:00
    assert dash.bonus_offered == 4 and dash.bonus_completed == 2
    assert any("bonus" in line for line in dash.insights)
    assert any("üretken saat" in line for line in dash.insights)
    # Utandırma yasak + Wrapped kilidi: story kartlarında kaçırılan geçmez.
    assert all("yine yapmadın" not in line for line in dash.insights)
    for card in recap.cards:
        assert "kaçır" not in card.subtitle.lower()
        assert "ceza" not in card.subtitle.lower()


def test_dashboard_patterns_degrade_without_log():
    """Log/bonus verisi yoksa alanlar boş kalır — rapor düşmez."""
    recap = recap_service.build_recap(
        state=GameState(user_id="u"), plan=_plan_with_done_tasks(2),
    )
    dash = recap.dashboard
    assert dash is not None
    assert dash.hour_done == []
    assert dash.bonus_offered == 0
    assert len(dash.weekday_done) == 7


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

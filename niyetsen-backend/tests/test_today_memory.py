"""Sohbet belleği — bugünün nabzı Türkçe + plan uzatma uyarısı."""
from datetime import date, timedelta

from app.models.schemas import Plan, PlanDay, Task
from app.services import project_service
from app.storage.repository import repo


def test_today_memory_uses_turkish_status_labels():
    user_id = "memory-tr-user"
    today = date.today()
    repo.save_plan(
        user_id,
        Plan(
            id="plan_mem",
            duration_days=30,
            batch_generated_until=1,
            start_date=today,
            days=[
                PlanDay(
                    day=1,
                    theme="Başlangıç",
                    tasks=[
                        Task(
                            id="t1",
                            day=1,
                            date=today,
                            title="Yürüyüş",
                            categories=["İrade"],
                            status="pending",
                        )
                    ],
                )
            ],
            name="Planım",
            slot_no=1,
            is_active=True,
        ),
    )
    today_status, recent = project_service.describe_today_for_memory(repo, user_id)
    assert "bekliyor" in today_status
    assert "pending" not in today_status
    assert "Yürüyüş" in today_status
    assert "Yürüyüş" in recent


def test_today_memory_points_to_today_tab_when_extension_needed():
    user_id = "memory-ext-user"
    start = date.today() - timedelta(days=20)
    repo.save_plan(
        user_id,
        Plan(
            id="plan_ext",
            duration_days=180,
            batch_generated_until=7,
            start_date=start,
            days=[
                PlanDay(
                    day=1,
                    theme="Eski parti",
                    tasks=[
                        Task(
                            id="old",
                            day=1,
                            date=start,
                            title="Eski halka",
                            categories=["İstikrar"],
                            status="done",
                        )
                    ],
                )
            ],
            name="Kampüs",
            slot_no=1,
            is_active=True,
        ),
    )
    today_status, _recent = project_service.describe_today_for_memory(repo, user_id)
    assert "Bugünün halkası henüz açılmamış" in today_status
    assert "görev uydurma" in today_status

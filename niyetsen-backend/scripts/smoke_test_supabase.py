"""
Niyetsen — Supabase round-trip smoke testi (elle çalıştırılır, pytest'e dahil değil).
Gerçek Supabase projesine yazıp okur; sadece USE_SUPABASE_DB=true + secrets doluyken anlamlıdır.

Kullanım:
    cd niyetsen-backend
    python -m scripts.smoke_test_supabase
"""
from __future__ import annotations

import sys
from datetime import date

from app.config import settings
from app.models.schemas import GameState, Plan, PlanDay, Task

SMOKE_USER_ID = "smoke_test_user"


def main() -> None:
    if not settings.USE_SUPABASE_DB:
        print("❌ USE_SUPABASE_DB=false — önce .env'de true yap.")
        sys.exit(1)
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL veya SUPABASE_SERVICE_KEY boş — .env'i doldur.")
        sys.exit(1)

    from app.storage.supabase_repository import SupabaseRepository

    repo = SupabaseRepository()

    print(f"→ get_state({SMOKE_USER_ID}) (yoksa users satırı otomatik oluşur)")
    state = repo.get_state(SMOKE_USER_ID)
    assert state.user_id == SMOKE_USER_ID
    print(f"  OK — points={state.points}")

    print("→ save_state (puan + streak güncelle)")
    state.points["İrade"] = 150
    state.streak_len = 3
    state.excuse_count = 1
    repo.save_state(state)
    reloaded = repo.get_state(SMOKE_USER_ID)
    assert reloaded.points["İrade"] == 150, "points round-trip başarısız"
    assert reloaded.streak_len == 3, "streak_len round-trip başarısız"
    assert reloaded.excuse_count == 1, "excuse_count round-trip başarısız"
    print(f"  OK — kaydedilen puan/streak geri okundu: points={reloaded.points}, streak={reloaded.streak_len}")

    print("→ save_plan + get_plan (1 günlük mini plan)")
    task = Task(
        id="smoke_task_1",
        day=1,
        title="Smoke test görevi",
        categories=["İrade"],
        image_keyword="test",
        image_url="https://example.com/x.jpg",
        tiny_version="1 dakika dur",
        status="pending",
        date=date.today(),
    )
    plan = Plan(
        id="smoke_plan_1",
        duration_days=1,
        batch_generated_until=1,
        start_date=date.today(),
        days=[PlanDay(day=1, theme="Test günü", tasks=[task])],
    )
    repo.save_plan(SMOKE_USER_ID, plan)
    fetched = repo.get_plan(SMOKE_USER_ID)
    assert fetched is not None, "get_plan None döndü"
    assert fetched.id == "smoke_plan_1"
    assert len(fetched.days) == 1 and len(fetched.days[0].tasks) == 1
    assert fetched.days[0].tasks[0].title == "Smoke test görevi"
    print(f"  OK — plan geri okundu: {fetched.id}, gün sayısı={len(fetched.days)}")

    print("→ get_task + update_task + proof_attempts")
    fetched_task = repo.get_task(SMOKE_USER_ID, "smoke_task_1")
    assert fetched_task is not None
    fetched_task.status = "done"
    repo.update_task(SMOKE_USER_ID, fetched_task)
    after_update = repo.get_task(SMOKE_USER_ID, "smoke_task_1")
    assert after_update.status == "done", "update_task round-trip başarısız"

    n1 = repo.incr_proof_attempts(SMOKE_USER_ID, "smoke_task_1")
    n2 = repo.incr_proof_attempts(SMOKE_USER_ID, "smoke_task_1")
    assert n1 == 1 and n2 == 2, f"proof_attempts sayaç hatalı: {n1}, {n2}"
    print(f"  OK — proof_attempts artıyor: {n1} → {n2}")

    print("\n✅ Tüm Supabase round-trip testleri geçti. Supabase tablolarında "
          f"'{SMOKE_USER_ID}' kullanıcısını kontrol edebilirsin (Table Editor).")


if __name__ == "__main__":
    main()

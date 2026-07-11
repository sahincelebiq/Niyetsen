"""
Niyetsen — Supabase round-trip smoke testi (elle çalıştırılır, pytest'e dahil değil).
Gerçek Supabase projesine yazıp okur; sadece USE_SUPABASE_DB=true + secrets doluyken anlamlıdır.

Kullanım:
    cd niyetsen-backend
    python -m scripts.smoke_test_supabase
"""
from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timezone

from app.config import settings
from app.models.schemas import (
    BonusOffer, ChatMessage, CollectedIntent, ConsentRecord, Plan, PlanDay,
    ProofRecord, PushTokenRecord, ScoreEvent, Task,
)

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

    # Not: script tekrar tekrar aynı smoke_test_user'a karşı çalıştırılabilir
    # (kasıtlı — Table Editor'de kalıcı örnek veri bırakır), bu yüzden mutlak
    # değer değil ARTIŞ (delta) doğrulanır.
    before_attempts = repo.get_proof_attempts(SMOKE_USER_ID, "smoke_task_1")
    n1 = repo.incr_proof_attempts(SMOKE_USER_ID, "smoke_task_1")
    n2 = repo.incr_proof_attempts(SMOKE_USER_ID, "smoke_task_1")
    assert n1 == before_attempts + 1 and n2 == before_attempts + 2, (
        f"proof_attempts sayaç hatalı: {n1}, {n2}"
    )
    print(f"  OK — proof_attempts artıyor: {n1} → {n2}")

    print("→ chat_msgs (append_chat_message + get_chat_history)")
    before = len(repo.get_chat_history(SMOKE_USER_ID))
    repo.append_chat_message(SMOKE_USER_ID, ChatMessage(role="assistant", content="Merhaba 🌙"))
    repo.append_chat_message(SMOKE_USER_ID, ChatMessage(role="user", content="İstanbul'dayım"))
    hist = repo.get_chat_history(SMOKE_USER_ID)
    assert len(hist) == before + 2, "chat_msgs round-trip başarısız"
    assert hist[-2].role == "assistant" and hist[-1].content == "İstanbul'dayım"
    print(f"  OK — sohbet geçmişi kalıcı: {len(hist)} mesaj")

    print("→ intents (save_intent)")
    repo.save_intent(
        SMOKE_USER_ID,
        CollectedIntent(city="İstanbul", interests=["spor"], weekly_hours=5),
        duration_days=365,
    )
    print("  OK — niyet kaydedildi")

    print("→ Faz 3 proofs Storage + proofs + point_log")
    proof_id = f"smoke-{uuid.uuid4()}"
    proof_url = repo.store_proof_photo(
        SMOKE_USER_ID,
        "smoke_task_1",
        b"\x89PNG\r\n\x1a\n" + (b"\0" * 200),
        "image/png",
    )
    repo.save_proof(
        SMOKE_USER_ID,
        ProofRecord(
            id=proof_id,
            task_id="smoke_task_1",
            photo_url=proof_url,
            confidence_score=88,
            attempt_no=1,
        ),
    )
    assert any(
        proof.id == proof_id
        for proof in repo.get_proofs(SMOKE_USER_ID, "smoke_task_1")
    ), "proofs round-trip başarısız"
    reason = f"smoke:{proof_id}"
    before_logs = len(repo.get_point_log(SMOKE_USER_ID))
    repo.append_point_log(
        SMOKE_USER_ID,
        "smoke_task_1",
        [ScoreEvent(category="İrade", delta=50, reason=reason)],
    )
    logs = repo.get_point_log(SMOKE_USER_ID)
    assert len(logs) == before_logs + 1 and logs[-1].reason == reason, (
        "point_log round-trip başarısız"
    )
    print("  OK — private Storage, proofs ve point_log yazma/okuma başarılı")

    # Tekrarlanabilir smoke testi: yalnız bu koşunun Faz 3 artefaktlarını temizle.
    storage_path = proof_url.removeprefix("storage://proofs/")
    repo._db.table("point_log").delete().eq("reason", reason).execute()
    repo._db.table("proofs").delete().eq("id", proof_id).execute()
    repo._db.storage.from_("proofs").remove([storage_path])

    print("→ Faz 4 consent + push token + bonus atomik tamamlama")
    repo.save_consent(
        SMOKE_USER_ID,
        ConsentRecord(
            kind="ai_chat_processing",
            version=settings.AI_CHAT_CONSENT_VERSION,
            accepted=True,
        ),
    )
    assert any(
        row.kind == "ai_chat_processing" and row.accepted
        for row in repo.get_consents(SMOKE_USER_ID)
    ), "user_consents round-trip başarısız"

    push_token = "ExpoPushToken[smoke-test-token]"
    repo.upsert_push_token(PushTokenRecord(
        user_id=SMOKE_USER_ID,
        token=push_token,
        platform="ios",
    ))
    assert any(
        row.user_id == SMOKE_USER_ID and row.token == push_token
        for row in repo.list_notification_recipients()
    ), "push_tokens round-trip başarısız"

    repo._db.table("bonus_offers").delete().eq(
        "user_id", SMOKE_USER_ID
    ).eq("day", date.today().isoformat()).execute()
    offer_id = str(uuid.uuid4())
    offer = repo.save_bonus_offer(BonusOffer(
        id=offer_id,
        user_id=SMOKE_USER_ID,
        bonus_key="smoke",
        title="Smoke bonus",
        tiny_instruction="Bir adım at.",
        category="İrade",
        day=date.today(),
        offered_at=datetime.now(timezone.utc),
    ))
    assert offer.id == offer_id
    assert repo.claim_bonus_completion(
        SMOKE_USER_ID, offer_id, f"smoke-completion-{offer_id}"
    )
    after_bonus = repo.get_state(SMOKE_USER_ID)
    assert after_bonus.points["İrade"] == 160, "bonus +10 uygulanmadı"
    assert any(
        row.reason == f"motivasyon bonus görevi:{offer_id}"
        for row in repo.get_point_log(SMOKE_USER_ID)
    ), "bonus point_log yazılmadı"
    print("  OK — versioned consent, push token ve idempotent +10 bonus başarılı")

    repo._db.table("point_log").delete().eq(
        "reason", f"motivasyon bonus görevi:{offer_id}"
    ).execute()
    repo._db.table("bonus_offers").delete().eq("id", offer_id).execute()
    repo._db.table("push_tokens").delete().eq("token", push_token).execute()
    after_bonus.points["İrade"] = 150
    repo.save_state(after_bonus)

    print("\n✅ Tüm Supabase round-trip testleri geçti. Supabase tablolarında "
          f"'{SMOKE_USER_ID}' kullanıcısını kontrol edebilirsin (Table Editor).")


if __name__ == "__main__":
    main()

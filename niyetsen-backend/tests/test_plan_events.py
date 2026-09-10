"""Dilim 1: plan etkinlikleri + fotosuz Yaptım + zincir / ceza ayrımı."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import GameState, Plan, PlanDay, Task
from app.services import event_service, task_lifecycle_service, tool_service
from app.storage.repository import InMemoryRepository

client = TestClient(app)

USER = "plan-event-user"
START = date(2026, 9, 11)


def _headers(user_id: str = USER) -> dict[str, str]:
    return {"X-User-Id": user_id}


def _seed_plan(repo: InMemoryRepository, *, with_task: bool = True) -> Plan:
    tasks = []
    if with_task:
        tasks.append(
            Task(
                id="task-365",
                day=1,
                date=START,
                title="Sabah yürüyüşü",
                categories=["İrade"],
            )
        )
    plan = Plan(
        id="plan-ev-1",
        duration_days=30,
        batch_generated_until=7,
        start_date=START,
        days=[PlanDay(day=1, theme="Başlangıç", tasks=tasks)],
        name="Sağlıklı Beslenme",
    )
    repo.save_plan(USER, plan)
    return plan


def _freeze_today(monkeypatch, day: date = START) -> None:
    """Route + servis katmanı 'bugün'ü START sayar (gerçek takvimden bağımsız)."""
    monkeypatch.setattr("app.api.routes._user_today", lambda _tz: day)
    monkeypatch.setattr(
        "app.services.project_service._user_local_today", lambda _tz: day
    )


def test_infer_categories_from_title():
    assert event_service.infer_categories("100 şınav çek") == ["İrade", "Disiplin"]
    assert event_service.infer_categories("1 saat uyu") == ["Özsaygı"]
    assert event_service.infer_categories("bilinmeyen iş") == ["İstikrar"]


def test_infer_categories_short_roots_need_word_boundary():
    # "ara" (Sosyallik) ve "uyu" (Özsaygı) kökleri kelime içinde tetiklenmez.
    assert event_service.infer_categories("Para biriktir") == ["İstikrar"]
    assert event_service.infer_categories("Uyum toplantısı") == ["İstikrar"]
    assert event_service.infer_categories("Annemi ara") == ["Sosyallik"]
    assert event_service.infer_categories("Kitap oku 20 sayfa") == ["Disiplin", "İstikrar"]


def test_create_event_rejects_bad_clock_and_weekday(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo)
    bad_clock = client.post(
        "/plan/plan-ev-1/events",
        headers=_headers(),
        json={"title": "x", "scheduled_time": "99:99", "start_date": START.isoformat()},
    )
    assert bad_clock.status_code == 422
    bad_weekday = client.post(
        "/plan/plan-ev-1/events",
        headers=_headers(),
        json={
            "title": "x", "scheduled_time": "09:00", "start_date": START.isoformat(),
            "recurrence": "weekly", "byweekday": [7],
        },
    )
    assert bad_weekday.status_code == 422
    bad_range = client.post(
        "/plan/plan-ev-1/events",
        headers=_headers(),
        json={
            "title": "x", "scheduled_time": "09:00", "start_date": START.isoformat(),
            "end_date": (START - timedelta(days=1)).isoformat(),
        },
    )
    assert bad_range.status_code == 422
    other_plan = client.post(
        "/plan/baskasinin-plani/events",
        headers=_headers(),
        json={"title": "x", "scheduled_time": "09:00", "start_date": START.isoformat()},
    )
    assert other_plan.status_code == 404


def test_weekly_without_byweekday_defaults_to_start_weekday(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo)
    event = event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="Haftalık plan",
        scheduled_time="10:00", start_date=START, recurrence="weekly", today=START,
    )
    assert event.byweekday == [START.weekday()]
    assert event_service.occurs_on(event, START + timedelta(days=7)) is True
    assert event_service.occurs_on(event, START + timedelta(days=1)) is False


def test_future_event_has_no_occurrence_today_and_cannot_complete_early(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    future = START + timedelta(days=3)
    res = client.post(
        "/plan/plan-ev-1/events",
        headers=_headers(),
        json={"title": "Diş randevusu", "scheduled_time": "15:00",
              "start_date": future.isoformat()},
    )
    assert res.status_code == 200, res.text
    assert res.json()["occurrences"] == []
    daily = client.get("/tasks/daily", headers=_headers()).json()
    assert daily["events"] == []
    # Gelecek occurrence elle açılsa bile erken Yaptım reddedilir.
    event = isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1")[0]
    occ = isolated_in_memory_repo.ensure_event_occurrence(event, future)
    early = client.post(f"/plan/events/{occ.id}/complete", headers=_headers())
    assert early.status_code == 400


def test_complete_twice_returns_409_and_awards_once(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    created = event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="1 saat uyu",
        scheduled_time="23:00", start_date=START, today=START,
    )
    occ_id = created.occurrences[0].id
    first = client.post(f"/plan/events/{occ_id}/complete", headers=_headers())
    assert first.status_code == 200
    assert first.json()["points"]["Özsaygı"] == 50
    second = client.post(f"/plan/events/{occ_id}/complete", headers=_headers())
    assert second.status_code == 409
    assert isolated_in_memory_repo.get_state(USER).points["Özsaygı"] == 50
    log = isolated_in_memory_repo.get_point_log(USER)
    assert sum(1 for rec in log if rec.task_id == occ_id) == 1
    missing = client.post("/plan/events/yok-boyle-bir-sey/complete", headers=_headers())
    assert missing.status_code == 404


def test_delete_event_removes_occurrences_and_daily_entry(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    created = event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="100 şınav çek",
        scheduled_time="14:00", start_date=START, recurrence="daily", today=START,
    )
    assert client.get("/tasks/daily", headers=_headers()).json()["events"]
    stranger = client.delete(f"/plan/events/{created.id}", headers=_headers("baskasi"))
    assert stranger.status_code == 404
    res = client.delete(f"/plan/events/{created.id}", headers=_headers())
    assert res.status_code == 200
    assert isolated_in_memory_repo.list_plan_events(USER) == []
    assert isolated_in_memory_repo.list_event_occurrences_for_date(USER, START) == []
    assert client.get("/tasks/daily", headers=_headers()).json()["events"] == []
    again = client.delete(f"/plan/events/{created.id}", headers=_headers())
    assert again.status_code == 404


def test_daily_survives_event_storage_failure(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    """Degrade kuralı: etkinlik altyapısı patlasa Bugün 365 görevleriyle açılır."""
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)

    def boom(*_args, **_kwargs):
        raise RuntimeError("plan_events tablosu yok")

    monkeypatch.setattr(isolated_in_memory_repo, "list_plan_events", boom)
    daily = client.get("/tasks/daily", headers=_headers())
    assert daily.status_code == 200
    body = daily.json()
    assert body["items"][0]["task"]["id"] == "task-365"
    assert body["events"] == []


def test_list_plan_events_endpoint_scoped_to_owner(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo)
    event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="Meditasyon",
        scheduled_time="07:00", start_date=START, recurrence="daily", today=START,
    )
    mine = client.get("/plan/plan-ev-1/events", headers=_headers())
    assert mine.status_code == 200
    assert [e["title"] for e in mine.json()] == ["Meditasyon"]
    assert mine.json()[0]["categories"] == ["Özsaygı", "İstikrar"]
    theirs = client.get("/plan/plan-ev-1/events", headers=_headers("baskasi"))
    assert theirs.status_code == 404


def test_create_daily_event_appears_on_today(
    isolated_in_memory_repo: InMemoryRepository,
    monkeypatch,
):
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    res = client.post(
        "/plan/plan-ev-1/events",
        headers=_headers(),
        json={
            "title": "100 şınav çek",
            "scheduled_time": "14:00",
            "start_date": START.isoformat(),
            "recurrence": "daily",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["title"] == "100 şınav çek"
    assert body["categories"] == ["İrade", "Disiplin"]
    assert "image_url" not in body or not body.get("image_url")

    daily = client.get("/tasks/daily", headers=_headers()).json()
    assert daily["items"][0]["task"]["id"] == "task-365"
    assert len(daily["events"]) == 1
    assert daily["events"][0]["title"] == "100 şınav çek"
    assert daily["events"][0]["scheduled_time"] == "14:00"
    assert daily["events"][0]["status"] == "pending"


def test_complete_event_awards_points_no_proof(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    created = event_service.create_event(
        isolated_in_memory_repo,
        USER,
        plan_id="plan-ev-1",
        title="1 saat uyu",
        scheduled_time="23:00",
        start_date=START,
        recurrence="none",
        today=START,
    )
    occ = created.occurrences[0]
    result = client.post(
        f"/plan/events/{occ.id}/complete",
        headers=_headers(),
    )
    assert result.status_code == 200, result.text
    state = isolated_in_memory_repo.get_state(USER)
    assert state.points["Özsaygı"] == 50
    occ_after = isolated_in_memory_repo.get_event_occurrence(USER, occ.id)
    assert occ_after is not None
    assert occ_after.status == "done"


def test_missed_event_is_not_silent_penalized(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo, with_task=False)
    event_service.create_event(
        isolated_in_memory_repo,
        USER,
        plan_id="plan-ev-1",
        title="1 saat uyu",
        scheduled_time="23:00",
        start_date=START,
        recurrence="none",
        today=START,
    )
    isolated_in_memory_repo.save_state(GameState(user_id=USER, last_active_date=START - timedelta(days=1), streak_len=3))
    result = task_lifecycle_service.close_user_day(
        isolated_in_memory_repo, USER, START
    )
    assert result["penalized_tasks"] == 0
    assert isolated_in_memory_repo.get_state(USER).points["Özsaygı"] == 0
    occs = isolated_in_memory_repo.list_event_occurrences_for_date(USER, START)
    assert occs and occs[0].status == "pending"
    # Etkinlik kaçınca zincir kırılmaz (görevsiz gün + pending event = skip/koru)
    assert result["streak"] in ("skipped", "frozen", "extended")
    assert isolated_in_memory_repo.get_state(USER).streak_len == 3


def test_completed_event_saves_streak_when_365_missed(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo, with_task=True)
    created = event_service.create_event(
        isolated_in_memory_repo,
        USER,
        plan_id="plan-ev-1",
        title="100 şınav çek",
        scheduled_time="14:00",
        start_date=START,
        recurrence="none",
        today=START,
    )
    event_service.complete_occurrence(
        isolated_in_memory_repo, USER, created.occurrences[0].id, today=START
    )
    isolated_in_memory_repo.save_state(
        GameState(
            user_id=USER,
            last_active_date=START - timedelta(days=1),
            streak_len=5,
            points={"İrade": 100, "İstikrar": 0, "Disiplin": 0, "Özgüven": 0, "Sosyallik": 0, "Özsaygı": 0},
        )
    )
    # complete_occurrence already added +50; reset points for close_day assertion
    state = isolated_in_memory_repo.get_state(USER)
    state.points["İrade"] = 500
    state.points["Disiplin"] = 500
    isolated_in_memory_repo.save_state(state)

    result = task_lifecycle_service.close_user_day(
        isolated_in_memory_repo, USER, START
    )
    assert result["penalized_tasks"] == 1
    assert isolated_in_memory_repo.get_task(USER, "task-365").status == "missed_silent"
    assert result["streak"] == "extended"
    assert isolated_in_memory_repo.get_state(USER).streak_len == 6


def test_event_only_day_complete_extends_streak(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo, with_task=False)
    created = event_service.create_event(
        isolated_in_memory_repo,
        USER,
        plan_id="plan-ev-1",
        title="1 saat uyu",
        scheduled_time="23:00",
        start_date=START,
        recurrence="none",
        today=START,
    )
    event_service.complete_occurrence(
        isolated_in_memory_repo, USER, created.occurrences[0].id, today=START
    )
    isolated_in_memory_repo.save_state(
        GameState(user_id=USER, last_active_date=START - timedelta(days=1), streak_len=2)
    )
    result = task_lifecycle_service.close_user_day(
        isolated_in_memory_repo, USER, START
    )
    assert result["penalized_tasks"] == 0
    assert result["streak"] == "extended"
    assert isolated_in_memory_repo.get_state(USER).streak_len == 3


def test_plan_agent_thread_hidden_from_global_list(
    isolated_in_memory_repo: InMemoryRepository,
):
    from app.models.schemas import ChatMessage

    _seed_plan(isolated_in_memory_repo)
    isolated_in_memory_repo.append_chat_messages(USER, [
        ChatMessage(id="g1", role="user", content="global sohbet"),
    ])
    thread = isolated_in_memory_repo.get_or_create_plan_agent_thread(USER, "plan-ev-1")
    isolated_in_memory_repo.append_chat_messages_to_thread(
        USER,
        thread.id,
        [ChatMessage(id="p1", role="user", content="plana 100 şınav ekle")],
    )
    listed = isolated_in_memory_repo.list_chat_threads(USER)
    assert all(t.id != thread.id for t in listed)
    http = client.get("/chat/threads", headers=_headers()).json()
    assert all(t["id"] != thread.id for t in http)


def test_etkinlik_olustur_tool_creates_event_not_365_task(
    isolated_in_memory_repo: InMemoryRepository,
):
    from app.models.schemas import ToolCall

    _seed_plan(isolated_in_memory_repo)
    calls, messages = tool_service.dispatch(
        isolated_in_memory_repo,
        USER,
        [ToolCall(
            name="etkinlik_olustur",
            args={
                "title": "100 şınav çek",
                "date": START.isoformat(),
                "time": "14:00",
                "recurrence": "daily",
            },
        )],
        plan_id="plan-ev-1",
    )
    assert messages
    events = isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1")
    assert len(events) == 1
    plan = isolated_in_memory_repo.get_plan(USER)
    assert all(t.id == "task-365" for d in plan.days for t in d.tasks)


def test_etkinlik_tool_without_date_uses_today_and_normalizes_time(
    isolated_in_memory_repo: InMemoryRepository,
):
    """Model tarih uydurmaz: date yoksa 'bugün'; geçmiş tarih bugüne çekilir;
    '9.00' → '09:00'; byweekday + süre işlenir; occurrence bugün açılır."""
    from app.models.schemas import ToolCall

    _seed_plan(isolated_in_memory_repo)
    calls, messages = tool_service.dispatch(
        isolated_in_memory_repo,
        USER,
        [
            ToolCall(name="etkinlik_olustur", args={"title": "Su iç", "time": "9.00"}),
            ToolCall(
                name="etkinlik_olustur",
                args={
                    "title": "Pilates",
                    "time": "18:30",
                    "date": "2020-01-01",
                    "recurrence": "weekly",
                    "byweekday": [0, 2, 9],
                    "duration_min": 9999,
                },
            ),
        ],
        plan_id="plan-ev-1",
        today=START,
    )
    assert calls == []  # sunucu aracı → cihaz aksiyonu yok
    assert len(messages) == 2
    events = {e.title: e for e in isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1")}
    su = events["Su iç"]
    assert su.scheduled_time == "09:00"
    assert su.start_date == START
    assert su.categories == ["Özsaygı", "İrade"]
    pilates = events["Pilates"]
    assert pilates.start_date == START  # geçmiş tarih bugüne çekildi
    assert pilates.byweekday == [0, 2]
    assert pilates.duration_min == event_service.MAX_DURATION_MIN
    occs = isolated_in_memory_repo.list_event_occurrences_for_date(USER, START)
    assert {o.event_id for o in occs} == {su.id}  # START Cuma; pilates Pzt/Çar


def test_etkinlik_tool_ignored_without_plan_or_bad_input(
    isolated_in_memory_repo: InMemoryRepository,
):
    from app.models.schemas import ToolCall

    _seed_plan(isolated_in_memory_repo)
    # Global sohbette plan_id yok → etkinlik aracı sessizce yoksayılır.
    _calls, messages = tool_service.dispatch(
        isolated_in_memory_repo, USER,
        [ToolCall(name="etkinlik_olustur", args={"title": "x", "time": "10:00"})],
    )
    assert messages == []
    # Saçma saat → hata mesajı, etkinlik yok, istisna yok.
    _calls, messages = tool_service.dispatch(
        isolated_in_memory_repo, USER,
        [ToolCall(name="etkinlik_olustur", args={"title": "x", "time": "saat üç"})],
        plan_id="plan-ev-1", today=START,
    )
    assert messages and "eklenemedi" in messages[0].casefold()
    assert isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1") == []


def test_ensure_event_occurrence_is_idempotent(
    isolated_in_memory_repo: InMemoryRepository,
):
    _seed_plan(isolated_in_memory_repo)
    event = event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="Meditasyon",
        scheduled_time="07:00", start_date=START, recurrence="daily", today=START,
    )
    first = isolated_in_memory_repo.ensure_event_occurrence(event, START)
    second = isolated_in_memory_repo.ensure_event_occurrence(event, START)
    assert first.id == second.id
    # Peş peşe iki Bugün çağrısı tek occurrence bırakır.
    event_service.list_daily_events(isolated_in_memory_repo, USER, START)
    event_service.list_daily_events(isolated_in_memory_repo, USER, START)
    assert len(isolated_in_memory_repo.list_event_occurrences_for_date(USER, START)) == 1


def test_describe_plan_for_agent_uses_target_plan_not_active(
    isolated_in_memory_repo: InMemoryRepository,
):
    """Ajan bağlamı hedef plan: aktif plan başka olsa da o planın etkinlikleri anlatılır."""
    _seed_plan(isolated_in_memory_repo)
    event_service.create_event(
        isolated_in_memory_repo, USER, plan_id="plan-ev-1", title="100 şınav çek",
        scheduled_time="14:00", start_date=START, recurrence="daily", today=START,
    )
    other = Plan(
        id="plan-ev-2", duration_days=30, batch_generated_until=7, start_date=START,
        days=[PlanDay(day=1, theme="Diğer", tasks=[])], name="Kariyer",
    )
    isolated_in_memory_repo.save_plan(USER, other)
    isolated_in_memory_repo.set_active_plan(USER, "plan-ev-2")
    assert isolated_in_memory_repo.get_plan(USER).id == "plan-ev-2"
    status, events_line = event_service.describe_plan_for_agent(
        isolated_in_memory_repo, USER, "plan-ev-1", START
    )
    assert "Sağlıklı Beslenme" in status
    assert "100 şınav çek" in events_line
    assert "14:00" in events_line
    assert "Kariyer" not in status


def test_plan_agent_chat_runs_tool_and_persists_thread(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    """Uçtan uca: Gemini stub'lı — araç çağrısı etkinlik yaratır, yanıt onaylar,
    plan-ajan thread'ine yazılır, global listede görünmez, collected değişmez."""
    from app.services import plan_agent_service
    from tests.conftest import grant_chat_consent

    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    grant_chat_consent(USER, client)

    async def fake_function_calls(_message, *, declarations, system_instruction=""):
        assert any(d["name"] == "etkinlik_olustur" for d in declarations)
        assert START.isoformat() in system_instruction
        assert "Sağlıklı Beslenme" in system_instruction
        return [{"name": "etkinlik_olustur", "args": {"title": "100 şınav çek", "time": "14:00", "recurrence": "daily"}}]

    captured: dict = {}

    async def fake_generate_json(contents, *, system_instruction="", **_kwargs):
        captured["contents"] = contents
        captured["system"] = system_instruction
        return {"reply": "Tamam, şınavı her gün 14:00'e ekledim.", "suggestions": ["Her sabah 07:00 su iç"]}

    monkeypatch.setattr(plan_agent_service, "generate_function_calls", fake_function_calls)
    monkeypatch.setattr(plan_agent_service, "generate_json", fake_generate_json)

    res = client.post(
        "/plan/plan-ev-1/chat",
        headers={**_headers(), "X-App-Locale": "en"},
        json={"messages": [{"role": "user", "content": "her gün 14:00 100 şınav ekle"}],
              "collected": {}},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ready_for_plan"] is False
    assert "ekledim" in body["reply"]
    assert body["suggestions"] == ["Her sabah 07:00 su iç"]
    events = isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1")
    assert [e.title for e in events] == ["100 şınav çek"]
    assert events[0].created_by == "agent"
    # Sunucu işlemi ve dil yönergesi bağlama girdi.
    joined = str(captured["contents"])
    assert "SUNUCU İŞLEMİ" in joined
    assert "YANIT DİLİ" in joined and "PLAN KİLİDİ" in joined
    assert "PLAN-İÇİ AJAN" in captured["system"]
    # Thread: plan ajanına yazıldı, global listede yok.
    history = client.get("/plan/plan-ev-1/chat/history", headers=_headers()).json()
    assert [m["role"] for m in history][-2:] == ["user", "assistant"]
    thread = isolated_in_memory_repo.get_or_create_plan_agent_thread(USER, "plan-ev-1")
    assert all(t.id != thread.id for t in isolated_in_memory_repo.list_chat_threads(USER))
    # Yabancı plana sohbet → 404.
    denied = client.post(
        "/plan/plan-ev-1/chat", headers=_headers("baskasi"),
        json={"messages": [{"role": "user", "content": "selam"}], "collected": {}},
    )
    assert denied.status_code in (403, 404)


def test_plan_agent_chat_survives_tool_detection_failure(
    isolated_in_memory_repo: InMemoryRepository, monkeypatch,
):
    from app.services import plan_agent_service
    from tests.conftest import grant_chat_consent

    _freeze_today(monkeypatch)
    _seed_plan(isolated_in_memory_repo)
    grant_chat_consent(USER, client)

    async def broken_function_calls(*_a, **_k):
        raise RuntimeError("function calling down")

    async def fake_generate_json(*_a, **_k):
        return {"reply": "Saat kaçta olsun?", "suggestions": []}

    monkeypatch.setattr(plan_agent_service, "generate_function_calls", broken_function_calls)
    monkeypatch.setattr(plan_agent_service, "generate_json", fake_generate_json)
    res = client.post(
        "/plan/plan-ev-1/chat",
        headers=_headers(),
        json={"messages": [{"role": "user", "content": "her gün şınav ekle"}], "collected": {}},
    )
    assert res.status_code == 200, res.text
    assert res.json()["reply"] == "Saat kaçta olsun?"
    assert isolated_in_memory_repo.list_plan_events(USER, "plan-ev-1") == []


def test_weekdays_recurrence_skips_sunday():
    from app.models.schemas import PlanEvent

    monday = date(2026, 9, 14)
    sunday = date(2026, 9, 13)
    event = PlanEvent(
        id="e1",
        user_id=USER,
        plan_id="plan-ev-1",
        title="şınav",
        categories=["İrade"],
        scheduled_time="14:00",
        recurrence="weekdays",
        start_date=date(2026, 9, 11),
    )
    assert event_service.occurs_on(event, monday) is True
    assert event_service.occurs_on(event, sunday) is False

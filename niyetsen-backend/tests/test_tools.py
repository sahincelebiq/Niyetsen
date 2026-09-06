import asyncio
from datetime import date

from app.core import prompts, tools
from app.models.schemas import (
    ChatMessage, ChatRequest, Plan, PlanDay, Task, ToolCall,
)
from app.services import intent_service, tool_service
from app.storage.repository import InMemoryRepository


def test_tool_allowlist_is_closed():
    assert tools.is_allowed("gorev_ertele_mazeretli")
    assert tools.is_allowed("alarm_kur")
    assert not tools.is_allowed("dosya_sil")
    assert not tools.is_allowed("odeme_yap")


def test_chat_returns_only_allowed_native_tool_calls(monkeypatch):
    async def fake_tool_calls(*args, **kwargs):
        return [
            {
                "name": "gorev_ertele_mazeretli",
                "args": {"task_id": "task-1", "excuse_text": "Hastayım"},
            },
            {"name": "odeme_yap", "args": {"amount": 100}},
        ]

    async def fake_json(*args, **kwargs):
        return {
            "reply": "Bugünkü görevi mazeretli olarak erteleyebilirim.",
            "ready_for_plan": False,
            "collected": {},
        }

    monkeypatch.setattr(intent_service, "generate_function_calls", fake_tool_calls)
    monkeypatch.setattr(intent_service, "generate_json", fake_json)

    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content="Hastayım, task-1 görevini mazeretli ertele.",
                    )
                ]
            )
        )
    )

    assert [call.name for call in response.tool_calls] == [
        "gorev_ertele_mazeretli"
    ]


def test_regular_chat_does_not_trigger_tool_model(monkeypatch):
    async def should_not_run(*args, **kwargs):
        raise AssertionError("Normal sohbet için tool modeli çağrılmamalı")

    async def fake_json(*args, **kwargs):
        return {
            "reply": "Seni dinliyorum.",
            "ready_for_plan": False,
            "collected": {},
        }

    monkeypatch.setattr(intent_service, "generate_function_calls", should_not_run)
    monkeypatch.setattr(intent_service, "generate_json", fake_json)

    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content="Bu yıl daha sağlıklı yaşamak istiyorum.",
                    )
                ]
            )
        )
    )
    assert response.tool_calls == []


def test_tool_detect_receives_context_and_chat_history(monkeypatch):
    captured = {}

    async def fake_tool_calls(*args, **kwargs):
        captured["contents"] = args[0] if args else kwargs.get("contents")
        captured["system"] = kwargs.get("system_instruction")
        return [
            {
                "name": "gorev_ertele_mazeretli",
                "args": {"task_id": "task-today", "excuse_text": "Hastayım"},
            }
        ]

    async def fake_json(*args, **kwargs):
        captured["reply_contents"] = args[0] if args else kwargs.get("contents")
        captured["reply_system"] = kwargs.get("system_instruction")
        return {
            "reply": "Bugünkü görevi mazeretli olarak erteleyebilirim.",
            "ready_for_plan": False,
            "collected": {},
        }

    monkeypatch.setattr(intent_service, "generate_function_calls", fake_tool_calls)
    monkeypatch.setattr(intent_service, "generate_json", fake_json)

    last_line = "Hastayım, bugünkü görevi mazeretli ertele."
    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="user", content="Bugün yürüyüş var mıydı?"),
                    ChatMessage(
                        role="assistant",
                        content="Evet, bugünün halkasında yürüyüş var.",
                    ),
                    ChatMessage(role="user", content=last_line),
                ]
            ),
            has_active_plan=True,
            plan_has_content=True,
            today_status=(
                "1 bekliyor. Görevler: Yürüyüş [bekliyor] task_id=task-today"
            ),
            recent_tasks="Yürüyüş (2026-09-06, bekliyor, task_id=task-today)",
        )
    )

    assert [call.name for call in response.tool_calls] == [
        "gorev_ertele_mazeretli"
    ]
    assert captured["contents"] != last_line
    assert "KULLANICI BELLEĞİ" in captured["contents"]
    assert "task_id=task-today" in captured["contents"]
    assert "--- SOHBET ---" in captured["contents"]
    assert "Bugün yürüyüş var mıydı?" in captured["contents"]
    assert last_line in captured["contents"]
    assert prompts.SYSTEM_PROMPT in captured["system"]
    assert "Aktif planı olan" not in captured["contents"]
    assert captured["reply_system"] == prompts.SYSTEM_PROMPT
    assert "task_id=task-today" in captured["reply_contents"]
    assert "Aktif planı olan" in captured["reply_contents"]


def _repo_with_task() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.save_plan(
        "tool-user",
        Plan(
            id="plan-1",
            duration_days=7,
            batch_generated_until=7,
            start_date=date(2026, 7, 10),
            days=[
                PlanDay(
                    day=1,
                    tasks=[
                        Task(
                            id="task-1",
                            day=1,
                            date=date(2026, 7, 10),
                            title="Yürüyüş",
                            categories=["İrade"],
                        )
                    ],
                )
            ],
        ),
    )
    return repository


def test_excuse_tool_uses_fixed_scoring_path():
    repository = _repo_with_task()
    state = repository.get_state("tool-user")
    state.points["İrade"] = 100
    state.silent_miss_streak = 3

    actions, messages = tool_service.dispatch(
        repository,
        "tool-user",
        [
            ToolCall(
                name="gorev_ertele_mazeretli",
                args={"task_id": "task-1", "excuse_text": "Hastayım"},
            )
        ],
    )

    assert actions == []
    assert repository.get_state("tool-user").points["İrade"] == 75
    assert repository.get_state("tool-user").silent_miss_streak == 0
    assert repository.get_task("tool-user", "task-1").status == "missed_excused"
    assert "sabit −25" in messages[0]


def test_device_tool_requires_owned_task():
    repository = _repo_with_task()
    actions, messages = tool_service.dispatch(
        repository,
        "another-user",
        [ToolCall(name="kanit_dogrula", args={"task_id": "task-1"})],
    )
    assert actions == []
    assert "sana ait değil" in messages[0]

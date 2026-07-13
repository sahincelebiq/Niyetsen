import asyncio

from app.models.schemas import ChatMessage, ChatRequest
from app.services import intent_service


def test_crisis_message_short_circuits_model(monkeypatch):
    async def should_not_run(*args, **kwargs):
        raise AssertionError("Kriz mesajında model çağrılmamalı")

    monkeypatch.setattr(intent_service, "generate_json", should_not_run)
    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="user", content="Yaşamak istemiyorum.")
                ]
            )
        )
    )
    assert response.crisis is True
    assert "gerçek bir insan" in response.reply


def test_crisis_message_detects_uppercase_turkish(monkeypatch):
    async def should_not_run(*args, **kwargs):
        raise AssertionError("Kriz mesajında model çağrılmamalı")

    monkeypatch.setattr(intent_service, "generate_json", should_not_run)
    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="user", content="İNTİHAR etmeyi düşünüyorum.")
                ]
            )
        )
    )
    assert response.crisis is True


def test_math_question_redirects_to_user_intent(monkeypatch):
    async def should_not_run(*args, **kwargs):
        raise AssertionError("Açık kapsam dışı soruda model çağrılmamalı")

    monkeypatch.setattr(intent_service, "generate_json", should_not_run)
    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(
                        role="user",
                        content="Matematik sorusu: 2+2 kaç eder?",
                    )
                ]
            )
        )
    )
    assert response.crisis is False
    assert "niyetinin rehberiyim" in response.reply


def test_active_plan_uses_guide_mode_and_memory(monkeypatch):
    captured = {}

    async def fake_json(*args, **kwargs):
        captured["contents"] = args[0] if args else kwargs.get("contents")
        return {
            "reply": "23 günlük zincirin ve tamamladığın yürüyüş güçlü bir kanıt.",
            "ready_for_plan": True,
            "collected": {},
        }

    monkeypatch.setattr(intent_service, "generate_json", fake_json)
    response = asyncio.run(
        intent_service.handle_chat(
            ChatRequest(
                messages=[
                    ChatMessage(role="user", content="Zincirim nasıl gidiyor?")
                ]
            ),
            has_active_plan=True,
            plan_has_content=True,
            today_status="1 done",
            recent_tasks="20 dakika yürüyüş (done)",
        )
    )
    assert response.ready_for_plan is False
    assert "Aktif planı olan" in captured["contents"]
    assert "Son görevler: 20 dakika yürüyüş (done)" in captured["contents"]

"""
Niyetsen — Niyet Toplama Servisi (çekirdek halkanın 1. yarısı)
Sohbet → eksik alanları soruyla doldur → ready_for_plan sinyali.
Hazırlık kararını MODELE bırakma: kod tarafında da doğrula (çifte kilit).
"""
from __future__ import annotations

import logging

from app.config import settings
from app.core import prompt_builder, prompts, tools
from app.core.gemini_client import generate_function_calls, generate_json
from app.models.schemas import (
    ChatRequest, ChatResponse, CollectedIntent, GameState, ToolCall,
)

log = logging.getLogger("niyetsen.intent")

MAX_CLARIFYING_QUESTIONS = 4  # kullanıcıyı yorma (algoritma belgesi kuralı)
TOOL_INTENT_MARKERS = (
    "mazeret", "ertele", "alarm kur", "hatırlatıcı kur", "takvime ekle",
    "kanıt", "fotoğraf", "yaptım", "görev oluştur", "görev ekle",
)
REPLAN_MARKERS = (
    "plan tasarla", "plan oluştur", "yeni plan", "kapsamlı plan",
    "yeniden plan", "plan yap", "planlama yap",
)
CHAT_HISTORY_LIMIT = 24


def _wants_replan(message: str) -> bool:
    normalized = message.casefold()
    return any(marker in normalized for marker in REPLAN_MARKERS)


def _use_intent_mode(has_active_plan: bool, plan_has_content: bool, message: str) -> bool:
    if not has_active_plan or not plan_has_content:
        return not has_active_plan
    return _wants_replan(message) or len(message) >= 120


def _merge_collected(old: CollectedIntent, new_raw: dict) -> CollectedIntent:
    """Modelin döndürdüğü collected'ı eskisiyle birleştir; model alan silemez."""
    merged = old.model_copy()
    if not isinstance(new_raw, dict):
        return merged
    if new_raw.get("city"):
        merged.city = str(new_raw["city"])
    if new_raw.get("interests"):
        seen = set(merged.interests)
        for i in new_raw["interests"]:
            if i and i not in seen:
                merged.interests.append(str(i))
                seen.add(i)
    if new_raw.get("weekly_hours") is not None:
        try:
            merged.weekly_hours = float(new_raw["weekly_hours"])
        except (TypeError, ValueError):
            pass
    if new_raw.get("duration_days"):
        try:
            merged.duration_days = int(new_raw["duration_days"])
        except (TypeError, ValueError):
            pass
    if new_raw.get("social_pref"):
        merged.social_pref = str(new_raw["social_pref"])
    if new_raw.get("budget"):
        merged.budget = str(new_raw["budget"])
    return merged


async def handle_chat(req: ChatRequest, state: GameState | None = None,
                user_name: str = "", birth_date: str = "", zodiac: str = "",
                active_intent: str = "", today_status: str = "",
                recent_tasks: str = "", mood_notes: str = "",
                has_active_plan: bool = False,
                plan_has_content: bool = False) -> ChatResponse:
    """/chat'in beyni. Kriz kontrolü ÖNCE — motivasyon her şeyden sonra gelir."""
    last_user_msg = next(
        (m.content for m in reversed(req.messages) if m.role == "user"), ""
    )

    # 1) GÜVENLİK AĞI (philosophy.py Yasa 5): kod tarafı kriz kontrolü
    if prompts.contains_crisis_signal(last_user_msg):
        return ChatResponse(
            reply=prompts.CRISIS_RESPONSE,
            ready_for_plan=False,
            collected=req.collected,
            crisis=True,
        )

    if prompts.contains_out_of_scope_signal(last_user_msg):
        return ChatResponse(
            reply=prompts.SCOPE_REDIRECT_RESPONSE,
            ready_for_plan=req.collected.is_ready(),
            collected=req.collected,
        )

    tool_calls: list[ToolCall] = []
    normalized_message = last_user_msg.casefold()
    if any(marker in normalized_message for marker in TOOL_INTENT_MARKERS):
        try:
            raw_calls = await generate_function_calls(
                last_user_msg,
                declarations=tools.TOOL_DECLARATIONS,
                system_instruction=(
                    "Yalnız kullanıcı açıkça bir işlem istiyorsa uygun aracı çağır. "
                    "Gerekli task_id bilinmiyorsa araç çağırma; kısa bir açıklama döndür. "
                    "Listede olmayan hiçbir işlemi çağırma."
                ),
            )
            tool_calls = [
                ToolCall(name=call["name"], args=call.get("args", {}))
                for call in raw_calls
                if tools.is_allowed(call.get("name", ""))
            ]
        except Exception:  # noqa: BLE001 — araç tespiti sohbeti düşürmemeli
            log.warning("Araç tespiti başarısız; sohbet devam ediyor.", exc_info=True)

    intent_mode = _use_intent_mode(has_active_plan, plan_has_content, last_user_msg)

    # 2) Bellek + bağlam kur (değişmez sıra: SYSTEM ayrı, CONTEXT + USER burada)
    memory = prompt_builder.build_memory_block(
        state=state,
        name=user_name,
        birth_date=birth_date,
        zodiac=zodiac,
        active_intent=active_intent,
        today_status=today_status,
        recent_tasks=recent_tasks,
        mood_notes=mood_notes,
    )
    history = [m.model_dump() for m in req.messages[-CHAT_HISTORY_LIMIT:]]
    contents = prompt_builder.build_chat_contents(
        context=prompt_builder.build_context(memory),
        history=history,
        extra_instructions=(
            (
                prompts.INTENT_JSON_INSTRUCTIONS
                if intent_mode else prompts.GUIDE_JSON_INSTRUCTIONS
            )
            + f"\n\nŞU ANA KADAR TOPLANAN: {req.collected.model_dump_json()}"
        ),
    )

    # 3) Model çağrısı (yapısal JSON)
    data = await generate_json(
        contents,
        system_instruction=prompts.SYSTEM_PROMPT,
        model=settings.GEMINI_MODEL,
        max_output_tokens=settings.GEMINI_CHAT_MAX_OUTPUT_TOKENS,
        json_retries=2,
        max_retries=2,
        response_schema=prompts.CHAT_RESPONSE_SCHEMA,
        disable_thinking=True,
    )

    merged = _merge_collected(req.collected, data.get("collected", {}))

    # 4) ÇİFTE KİLİT: plan zaten varsa veya asgari alanlar dolmadan plan yok.
    model_ready = bool(data.get("ready_for_plan"))
    can_generate_plan = not plan_has_content
    ready = can_generate_plan and (
        (model_ready and merged.is_ready())
        or (
            not has_active_plan
            and merged.is_ready()
            and sum(1 for m in req.messages if m.role == "assistant") >= MAX_CLARIFYING_QUESTIONS
        )
    )

    reply = str(data.get("reply") or "").strip() or (
        "Niyetini biraz daha anlat: bu yıl hayatında neyin değişmesini istiyorsun? ✨"
    )

    return ChatResponse(
        reply=reply,
        ready_for_plan=ready,
        collected=merged,
        tool_calls=tool_calls,
    )

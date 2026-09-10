"""Plan-içi ajan — global /chat'ten ayrı thread, yeni 365 plan üretmez.

Farklar (Şahin 2026-09-10):
- Bağlam HEDEF plandır (aktif plan değil): o planın bugünü + etkinlikleri.
- Araç listesi kapalı: etkinlik_olustur + alarm_kur + takvime_ekle.
- ready_for_plan her zaman False; thread_title yok (liste dışı thread).
- Araç tespiti bugünün tarihini bilir — "her gün 14:00 şınav" için tarih
  uydurmaz. Dil = uygulama dili (KULLANICI BELLEĞİ YANIT DİLİ satırı).
"""
from __future__ import annotations

import logging
from datetime import date

from app.config import settings
from app.core import prompt_builder, prompts, tools
from app.core.gemini_client import generate_function_calls, generate_json
from app.models.schemas import ChatRequest, ChatResponse, GameState, ToolCall
from app.services import tool_service
from app.storage.base import Repository

log = logging.getLogger("niyetsen.plan_agent")

_WEEKDAYS_TR = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")

# Araç tespiti pahalı bir Gemini çağrısıdır; yalnız etkinlik/hatırlatma
# niyeti taşıyan mesajlarda yapılır. Liste geniş — kaçırmamak, boşa çağırmaktan
# daha önemli.
EVENT_INTENT_MARKERS = (
    "ekle", "hatırlat", "hatirlat", "her gün", "her gun", "her sabah", "her akşam",
    "her aksam", "hafta içi", "hafta ici", "haftada", "saat", "sabah", "akşam",
    "aksam", "öğle", "ogle", "gece", "alarm", "takvim", "etkinlik", "rutin",
    "şınav", "sinav", "uyku", "uyu", "koş", "kos", "spor", "meditasyon", "kitap",
    "su iç", "yürüyüş", "yuruyus", "planla", "koy", "kur", ":",
    "pazartesi", "salı", "sali", "çarşamba", "carsamba", "perşembe", "persembe",
    "cuma", "cumartesi", "pazar", "yarın", "yarin", "bugün", "bugun",
)


def _wants_event_tool(message: str) -> bool:
    folded = message.casefold()
    if any(ch.isdigit() for ch in folded):
        return True
    return any(marker in folded for marker in EVENT_INTENT_MARKERS)


def _tool_system_instruction(today: date, plan_name: str) -> str:
    return (
        f"Bugün {today.isoformat()} ({_WEEKDAYS_TR[today.weekday()]}). "
        f"Bu sohbet «{plan_name or 'plan'}» planına kilitli. "
        "Kullanıcı bu plana etkinlik, rutin veya hatırlatma eklemek istiyorsa "
        "etkinlik_olustur çağır: date için tarih söylenmediyse bugünü yaz, "
        "'yarın' ise bugün+1; time 24 saat HH:MM; 'her gün' → daily, "
        "'hafta içi' → weekdays, belirli günler → weekly + byweekday (0=Pzt). "
        "Cihaz alarmı/takvimi açıkça istenirse alarm_kur veya takvime_ekle. "
        "Yeni 365 plan üretme; listede olmayan işlem çağırma. Emin değilsen "
        "araç çağırma."
    )


async def handle_plan_chat(
    repository: Repository,
    user_id: str,
    plan_id: str,
    req: ChatRequest,
    *,
    preferred_language: str = "tr",
    today_status: str = "",
    recent_tasks: str = "",
    today: date | None = None,
    state: GameState | None = None,
    user_name: str = "",
) -> ChatResponse:
    if not repository.plan_belongs_to_user(user_id, plan_id):
        raise ValueError("Plan bulunamadı.")
    last_user = next(
        (m.content for m in reversed(req.messages) if m.role == "user"), ""
    )
    if prompts.contains_crisis_signal(last_user):
        return ChatResponse(
            reply=prompts.CRISIS_RESPONSE,
            ready_for_plan=False,
            collected=req.collected,
            crisis=True,
        )

    plan = repository.get_plan_by_id(user_id, plan_id)
    plan_name = plan.name if plan else ""
    if not plan_name:
        plan_name = next(
            (s.name for s in repository.list_plan_summaries(user_id) if s.id == plan_id),
            "",
        )
    current = today or date.today()

    tool_calls: list[ToolCall] = []
    if _wants_event_tool(last_user):
        try:
            raw_calls = await generate_function_calls(
                last_user,
                declarations=tools.PLAN_AGENT_TOOL_DECLARATIONS,
                system_instruction=_tool_system_instruction(current, plan_name),
            )
            tool_calls = [
                ToolCall(name=call["name"], args=call.get("args", {}))
                for call in raw_calls
                if tools.is_allowed(call.get("name", ""))
            ]
        except Exception:  # noqa: BLE001 — araç tespiti sohbeti düşürmez
            log.warning("Plan-ajan araç tespiti atlandı", exc_info=True)

    # Araçlar cevaptan ÖNCE çalışır: model "eklendi" derken gerçekten eklenmiş
    # olur ve yanıt doğru bilgiye dayanır (global sohbetteki sıra tersiydi).
    device_actions, tool_messages = tool_service.dispatch(
        repository, user_id, tool_calls, plan_id=plan_id, today=current
    )

    plan_day = None
    duration_days = None
    if plan is not None:
        plan_day = (current - plan.start_date).days + 1
        duration_days = plan.duration_days
    memory = prompt_builder.build_memory_block(
        state=state,
        name=user_name,
        today_status=today_status,
        recent_tasks=recent_tasks,
        preferred_language=preferred_language,
        plan_day=plan_day,
        duration_days=duration_days,
    )
    lock_lines = [
        f"PLAN KİLİDİ: Bu sohbet yalnız «{plan_name or 'bu plan'}» planı için. "
        "Yeni kök plan / 365 niyet ÜRETİLMEZ.",
        f"Bugün: {current.isoformat()} ({_WEEKDAYS_TR[current.weekday()]}).",
    ]
    if tool_messages:
        lock_lines.append("SUNUCU İŞLEMİ (gerçekleşti): " + " ".join(tool_messages))
    context = prompt_builder.build_context("\n".join(lock_lines) + "\n" + memory, [])
    history = [m.model_dump() for m in req.messages[-24:]]
    contents = prompt_builder.build_chat_contents(
        context=context,
        history=history,
        extra_instructions=prompts.GUIDE_JSON_INSTRUCTIONS,
    )
    data = await generate_json(
        contents,
        system_instruction=prompts.SYSTEM_PROMPT + "\n" + prompts.PLAN_AGENT_ADDENDUM,
        model=settings.GEMINI_MODEL,
        max_output_tokens=settings.GEMINI_CHAT_MAX_OUTPUT_TOKENS,
        json_retries=2,
        max_retries=2,
        response_schema=prompts.CHAT_RESPONSE_SCHEMA,
        disable_thinking=True,
    )
    reply = str(data.get("reply") or "").strip() or (
        "Bu plana nasıl bir etkinlik ekleyelim?"
    )
    if tool_messages and not any(
        key in reply.casefold()
        for key in ("ekle", "added", "hinzugef", "ajout", "أض", "تمت")
    ):
        reply = f"{reply}\n\n" + " ".join(tool_messages)
    suggestions = [
        str(item).strip() for item in (data.get("suggestions") or []) if str(item).strip()
    ][:3]
    return ChatResponse(
        reply=reply,
        ready_for_plan=False,
        collected=req.collected,
        tool_calls=device_actions,
        suggestions=suggestions,
    )

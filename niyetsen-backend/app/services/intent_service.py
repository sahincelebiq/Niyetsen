"""
Niyetsen — Niyet Toplama Servisi (çekirdek halkanın 1. yarısı)
Sohbet → eksik alanları soruyla doldur → ready_for_plan sinyali.
Hazırlık kararını MODELE bırakma: kod tarafında da doğrula (çifte kilit).
"""
from __future__ import annotations

import logging

from app.core import prompt_builder, prompts
from app.core.gemini_client import generate_json
from app.models.schemas import ChatRequest, ChatResponse, CollectedIntent, GameState

log = logging.getLogger("niyetsen.intent")

MAX_CLARIFYING_QUESTIONS = 4  # kullanıcıyı yorma (algoritma belgesi kuralı)


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
                user_name: str = "", zodiac: str = "") -> ChatResponse:
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

    # 2) Bellek + bağlam kur (değişmez sıra: SYSTEM ayrı, CONTEXT + USER burada)
    memory = prompt_builder.build_memory_block(
        state=state, name=user_name, zodiac=zodiac
    )
    contents = prompt_builder.build_chat_contents(
        context=prompt_builder.build_context(memory),
        history=[m.model_dump() for m in req.messages],
        extra_instructions=(
            prompts.INTENT_JSON_INSTRUCTIONS
            + f"\n\nŞU ANA KADAR TOPLANAN: {req.collected.model_dump_json()}"
        ),
    )

    # 3) Model çağrısı (yapısal JSON)
    data = await generate_json(contents, system_instruction=prompts.SYSTEM_PROMPT)

    merged = _merge_collected(req.collected, data.get("collected", {}))

    # 4) ÇİFTE KİLİT: model "hazırım" dese de asgari alanlar dolmadan plan yok.
    model_ready = bool(data.get("ready_for_plan"))
    ready = model_ready and merged.is_ready()

    # 5) Soru yorgunluğu emniyeti: yeterli tur döndüyse ve asgari alanlar
    #    doluysa, model hâlâ soru soruyor olsa bile hazır say.
    assistant_turns = sum(1 for m in req.messages if m.role == "assistant")
    if not ready and merged.is_ready() and assistant_turns >= MAX_CLARIFYING_QUESTIONS:
        ready = True

    reply = str(data.get("reply") or "").strip() or (
        "Niyetini biraz daha anlat: bu yıl hayatında neyin değişmesini istiyorsun? ✨"
    )

    return ChatResponse(reply=reply, ready_for_plan=ready, collected=merged)

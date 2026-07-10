"""
Niyetsen — Plan Servisi (çekirdek halkanın 2. yarısı)
Niyet → Gemini'den yapısal JSON plan → her göreve görsel → birleşik plan.

Optimizasyon kararı: 365 gün TEK istekte üretilmez (maliyet + timeout + kalite
düşer). PLAN_BATCH_DAYS'lik partiler üretilir; kullanıcı ilerledikçe sonraki
parti çağrılır (generate_batch aynı fonksiyondur, start_day kaydırılır).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from app.config import CATEGORIES, settings
from app.core import prompts
from app.core.gemini_client import generate_json
from app.models.schemas import CollectedIntent, Plan, PlanDay, Task
from app.services.image_service import category_fallback_query, get_image

log = logging.getLogger("niyetsen.plan")


def _intent_block(collected: CollectedIntent, duration_days: int, start_day: int) -> str:
    return (
        f"Şehir: {collected.city}\n"
        f"İlgi alanları: {', '.join(collected.interests)}\n"
        f"Haftalık ayırabildiği saat: {collected.weekly_hours}\n"
        f"Toplam plan süresi: {duration_days} gün (şu an {start_day}. günden itibaren "
        f"{settings.PLAN_BATCH_DAYS} günlük bölüm üretiliyor)\n"
        f"Sosyal tercih: {collected.social_pref or 'belirtilmedi'}\n"
        f"Bütçe: {collected.budget or 'belirtilmedi'}"
    )


def _sanitize_categories(raw: list) -> list[str]:
    """Model kategori uydurursa ele — kapalı liste (config.CATEGORIES)."""
    clean = [c for c in (raw or []) if c in CATEGORIES]
    return clean or ["İstikrar"]  # etiketsiz görev kalmasın


async def generate_batch(
    collected: CollectedIntent,
    duration_days: int = 365,
    start_day: int = 1,
    start_date: date | None = None,
) -> Plan:
    """
    start_date: planın 1. gününün takvim tarihi (çapa). /plan/generate yeni bir
    plan açarken date.today() verir; /plan/next mevcut planın start_date'ini
    aynen geçirir ki sonraki partideki günler doğru takvim tarihine düşsün.
    """
    start_date = start_date or date.today()
    if not collected.is_ready():
        raise ValueError("Niyet eksik: şehir + ilgi + haftalık zaman dolmadan plan üretilmez.")

    batch = min(settings.PLAN_BATCH_DAYS, duration_days - start_day + 1)
    instructions = prompts.PLAN_JSON_INSTRUCTIONS.format(
        batch_days=batch,
        max_tasks=settings.MAX_TASKS_PER_DAY,
        intent_block=_intent_block(collected, duration_days, start_day),
    )

    data = await generate_json(instructions, system_instruction=prompts.SYSTEM_PROMPT)

    days: list[PlanDay] = []
    for d in (data.get("days") or [])[:batch]:
        day_no = start_day + len(days)
        tasks: list[Task] = []
        for t in (d.get("tasks") or [])[: settings.MAX_TASKS_PER_DAY]:
            title = str(t.get("title") or "").strip()
            if not title:
                continue
            categories = _sanitize_categories(t.get("categories"))
            keyword = str(t.get("image_keyword") or "").strip()
            if not keyword:
                keyword = category_fallback_query(categories)
            image = get_image(keyword, categories=categories)
            tasks.append(
                Task(
                    id=uuid.uuid4().hex[:12],
                    day=day_no,
                    date=start_date + timedelta(days=day_no - 1),
                    title=title,
                    task_type=t.get("task_type") if t.get("task_type") in
                        ("yer", "alışkanlık", "sosyal", "kişisel_gelişim") else "alışkanlık",
                    categories=categories,
                    image_keyword=keyword,
                    image_url=image.url,
                    image_source=image.source,
                    image_attribution=image.attribution,
                    image_attribution_url=image.attribution_url,
                    duration_min=int(t.get("duration_min") or 15),
                    tiny_version=str(t.get("tiny_version") or "2 dakikanı ayır ve sadece başla."),
                )
            )
        if tasks:
            days.append(PlanDay(day=day_no, theme=str(d.get("theme") or ""), tasks=tasks))

    if not days:
        raise ValueError("Model boş plan döndürdü — prompt veya niyet verisini kontrol et.")

    return Plan(
        id=uuid.uuid4().hex[:12],
        duration_days=duration_days,
        batch_generated_until=start_day + len(days) - 1,
        start_date=start_date,
        days=days,
    )

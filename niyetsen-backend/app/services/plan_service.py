"""
Niyetsen — Plan Servisi (çekirdek halkanın 2. yarısı)
Niyet → Gemini'den yapısal JSON plan → her göreve görsel → birleşik plan.

Optimizasyon kararı: 365 gün TEK istekte üretilmez (maliyet + timeout + kalite
düşer). PLAN_BATCH_DAYS'lik partiler üretilir; kullanıcı ilerledikçe sonraki
parti çağrılır (generate_batch aynı fonksiyondur, start_day kaydırılır).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, timedelta

from app.config import CATEGORIES, settings
from app.core import prompts
from app.core.gemini_client import generate_json
from app.models.schemas import CollectedIntent, Plan, PlanDay, Task
from app.services.image_service import category_fallback_query, enrich_image_keywords_batch, get_image_async

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

    data = await generate_json(
        instructions,
        system_instruction=prompts.SYSTEM_PROMPT,
        model=settings.GEMINI_MODEL_PLAN,
        max_output_tokens=8192,
        # Pro model 8192 token planı 30s'ye sığdıramıyordu; ayrılmış plan
        # zaman aşımı (varsayılan 90s) artık gerçekten kullanılıyor.
        timeout_sec=settings.GEMINI_PLAN_TIMEOUT_SEC,
    )

    raw_days = (data.get("days") or [])[:batch]
    pending_images: list[tuple[str, str, list[str]]] = []
    pending_meta: list[tuple[int, str, dict, list[str], str, str]] = []

    for day_index, day_payload in enumerate(raw_days):
        day_no = start_day + day_index
        theme = str(day_payload.get("theme") or "")
        for task_payload in (day_payload.get("tasks") or [])[: settings.MAX_TASKS_PER_DAY]:
            title = str(task_payload.get("title") or "").strip()
            if not title:
                continue
            categories = _sanitize_categories(task_payload.get("categories"))
            keyword = str(task_payload.get("image_keyword") or "").strip()
            if not keyword:
                keyword = category_fallback_query(categories)
            task_type = (
                task_payload.get("task_type")
                if task_payload.get("task_type") in
                ("yer", "alışkanlık", "sosyal", "kişisel_gelişim")
                else "alışkanlık"
            )
            pending_images.append((title, keyword, categories))
            pending_meta.append((day_no, theme, task_payload, categories, keyword, task_type))

    enriched_queries = await enrich_image_keywords_batch(
        pending_images,
        city=collected.city,
        interests=collected.interests,
    )

    # Görselleri SIRALI değil, sınırlı eşzamanlılıkla paralel çek:
    # 7 gün × 5 görev = 35 sıralı çağrı isteği dakikalarca bekletiyordu.
    image_semaphore = asyncio.Semaphore(5)

    async def _fetch_image(index: int) -> "object":
        day_no, theme, task_payload, categories, keyword, task_type = pending_meta[index]
        title = str(task_payload.get("title") or "").strip()
        search_query = enriched_queries[index] if index < len(enriched_queries) else keyword
        async with image_semaphore:
            return await get_image_async(
                search_query,
                categories=categories,
                title=title,
                city=collected.city,
                interests=collected.interests,
                task_type=task_type,
            )

    images = await asyncio.gather(
        *(_fetch_image(index) for index in range(len(pending_meta)))
    )

    day_tasks: dict[int, list[Task]] = {}
    day_themes: dict[int, str] = {}
    for index, (day_no, theme, task_payload, categories, keyword, task_type) in enumerate(pending_meta):
        title = str(task_payload.get("title") or "").strip()
        search_query = enriched_queries[index] if index < len(enriched_queries) else keyword
        image = images[index]
        task = Task(
            id=uuid.uuid4().hex[:12],
            day=day_no,
            date=start_date + timedelta(days=day_no - 1),
            title=title,
            task_type=task_type,
            categories=categories,
            image_keyword=search_query,
            image_url=image.url,
            image_source=image.source,
            image_attribution=image.attribution,
            image_attribution_url=image.attribution_url,
            duration_min=int(task_payload.get("duration_min") or 15),
            tiny_version=str(task_payload.get("tiny_version") or "2 dakikanı ayır ve sadece başla."),
        )
        day_tasks.setdefault(day_no, []).append(task)
        day_themes.setdefault(day_no, theme)

    days = [
        PlanDay(day=day_no, theme=day_themes.get(day_no, ""), tasks=day_tasks[day_no])
        for day_no in sorted(day_tasks)
    ]

    if not days:
        raise ValueError("Model boş plan döndürdü — prompt veya niyet verisini kontrol et.")

    return Plan(
        id=uuid.uuid4().hex[:12],
        duration_days=duration_days,
        batch_generated_until=start_day + len(days) - 1,
        start_date=start_date,
        days=days,
    )

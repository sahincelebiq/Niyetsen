"""
Niyetsen — Görsel Servisi
image_keyword → görsel URL. Ana kaynak Unsplash; hibrit modda Nano Banana
(gemini-2.5-flash-image) özel/spesifik görevlerde ve oransal olarak devreye girer.
Cursor notu (v2): Pinterest'e geçilirse SADECE bu dosya değişir; sözleşme
(get_image / get_image_async) aynı kalır.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings

log = logging.getLogger("niyetsen.image")

_UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
_CATEGORY_QUERIES = {
    "İrade": "determination workout",
    "İstikrar": "daily routine habit",
    "Disiplin": "focused study desk",
    "Özgüven": "confident person outdoor",
    "Sosyallik": "friends meeting cafe",
    "Özsaygı": "self care wellness",
}
_GEMINI_ATTRIBUTION = "AI generated · Nano Banana"
_GEMINI_SOURCE = "gemini_nano_banana"


@dataclass(frozen=True)
class ImageResult:
    url: str
    source: str
    attribution: str = ""
    attribution_url: str = ""


def _placeholder(keyword: str) -> str:
    """Anahtar yoksa / arama boş dönerse: deterministik, ücretsiz yer tutucu."""
    seed = "".join(ch for ch in keyword if ch.isalnum()) or "niyetsen"
    return f"https://picsum.photos/seed/{seed}/800/600"


def normalize_image_query(keyword: str) -> str:
    translated = (keyword or "").translate(str.maketrans({
        "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
        "ç": "c", "Ç": "C", "ö": "o", "Ö": "O", "ü": "u", "Ü": "U",
    }))
    ascii_text = unicodedata.normalize("NFKD", translated).encode(
        "ascii", "ignore"
    ).decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9 ]+", " ", ascii_text)).strip().lower()


def category_fallback_query(categories: list[str] | None) -> str:
    for category in categories or []:
        if category in _CATEGORY_QUERIES:
            return _CATEGORY_QUERIES[category]
    return "healthy daily routine"


def compose_image_query(
    keyword: str,
    *,
    title: str = "",
    city: str = "",
    interests: list[str] | None = None,
    categories: list[str] | None = None,
) -> str:
    """Görev + şehir + ilgi alanından bağlama uygun arama / görsel terimi."""
    parts: list[str] = []
    base = normalize_image_query(keyword) or normalize_image_query(title)
    if base:
        parts.append(base)

    city_part = normalize_image_query(city)
    if city_part and city_part not in " ".join(parts):
        parts.append(city_part)

    for interest in (interests or [])[:2]:
        token = normalize_image_query(interest)
        if token and token not in " ".join(parts):
            parts.append(token)
            break

    query = " ".join(parts).strip()
    if not query:
        return category_fallback_query(categories)
    return " ".join(query.split()[:6])


def should_use_gemini_image(
    *,
    title: str,
    keyword: str,
    task_type: str = "",
    categories: list[str] | None = None,
) -> bool:
    """Unsplash ana; Nano Banana özel görevler + IMAGE_GEMINI_RATIO ile ~yarı yarıya."""
    if not settings.GEMINI_API_KEY or not settings.IMAGE_GEMINI_ENABLED:
        return False

    normalized = normalize_image_query(keyword)
    specific_visual = (
        task_type in ("yer", "kişisel_gelişim")
        or len(normalized.split()) >= 4
        or len((title or "").split()) >= 5
    )
    ratio_pct = max(0.0, min(1.0, settings.IMAGE_GEMINI_RATIO)) * 100
    digest = int(hashlib.sha256(f"{title}:{keyword}".encode()).hexdigest(), 16) % 100
    ratio_pick = digest < ratio_pct

    return specific_visual or ratio_pick


def build_gemini_visual_prompt(
    *,
    title: str,
    keyword: str,
    city: str = "",
    interests: list[str] | None = None,
    categories: list[str] | None = None,
) -> str:
    """Nano Banana için somut, fotogerçekçi İngilizce görsel istemi."""
    query = compose_image_query(
        keyword,
        title=title,
        city=city,
        interests=interests,
        categories=categories,
    )
    category_hint = ", ".join(categories or []) or "personal growth"
    interest_hint = ", ".join((interests or [])[:2]) or "wellness"
    city_hint = city or "modern city"
    return (
        "Create a single inspiring lifestyle photograph for a daily habit task card. "
        "Photorealistic, warm natural light, 4:3 landscape composition, no text, "
        "no logos, no watermarks, no collage.\n"
        f"Task title: {title}\n"
        f"Visual focus: {query}\n"
        f"Category mood: {category_hint}\n"
        f"City context: {city_hint}\n"
        f"User interests: {interest_hint}"
    )


async def enrich_image_keywords_batch(
    items: list[tuple[str, str, list[str]]],
    *,
    city: str,
    interests: list[str],
) -> list[str]:
    """Tek Gemini çağrısıyla parti görevlerinin görsel terimlerini zenginleştirir."""
    if not items:
        return []

    fallbacks = [
        compose_image_query(keyword, title=title, city=city, interests=interests, categories=cats)
        for title, keyword, cats in items
    ]
    if not settings.GEMINI_API_KEY:
        return fallbacks

    from app.core.gemini_client import GeminiUnavailable, generate_json

    task_lines = "\n".join(
        f"{index + 1}. title={title!r} keyword={keyword!r} categories={cats!r}"
        for index, (title, keyword, cats) in enumerate(items)
    )
    interest_text = ", ".join(interests) if interests else "belirtilmedi"
    prompt = (
        f"Kullanıcı şehri: {city or 'belirtilmedi'}\n"
        f"İlgi alanları: {interest_text}\n\n"
        "Her görev için Unsplash araması veya AI görsel üretimi için İngilizce "
        "2-4 kelimelik, somut, küçük harf görsel terimi üret. Şehir ve ilgi alanına uygun olsun.\n\n"
        f"Görevler:\n{task_lines}\n\n"
        f'JSON: {{"queries": ["terim1", ...]}} — tam {len(items)} öğe, aynı sıra.'
    )
    try:
        data = await generate_json(
            prompt,
            model=settings.GEMINI_MODEL,
            max_output_tokens=512,
            json_retries=2,
            response_schema={
                "type": "object",
                "properties": {
                    "queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["queries"],
            },
            disable_thinking=True,
        )
        queries = data.get("queries") or []
        if len(queries) != len(items):
            return fallbacks
        enriched: list[str] = []
        for index, (title, keyword, cats) in enumerate(items):
            refined = normalize_image_query(str(queries[index]))
            enriched.append(
                refined
                or compose_image_query(
                    keyword, title=title, city=city, interests=interests, categories=cats
                )
            )
        return enriched
    except GeminiUnavailable as exc:
        log.warning("Görsel terim zenginleştirme atlandı: %s", exc)
        return fallbacks
    except Exception as exc:  # noqa: BLE001
        log.warning("Görsel terim zenginleştirme hatası: %s", exc)
        return fallbacks


def _search(query: str) -> list[dict]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    resp = httpx.get(
        _UNSPLASH_SEARCH,
        params={
            "query": query,
            "per_page": 10,
            "orientation": "landscape",
            "order_by": "relevant",
            "content_filter": "high",
        },
        headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _pick_result(results: list[dict], keyword: str) -> dict:
    candidates = results[:5]
    digest = int(hashlib.sha256(keyword.encode()).hexdigest(), 16)
    return candidates[digest % len(candidates)]


def _get_unsplash_image(
    keyword: str,
    *,
    categories: list[str] | None = None,
    title: str = "",
    city: str = "",
    interests: list[str] | None = None,
) -> ImageResult | None:
    query = compose_image_query(
        keyword,
        title=title,
        city=city,
        interests=interests,
        categories=categories,
    )
    fallback_query = category_fallback_query(categories)
    try:
        results = _search(query) if query else []
        source = "unsplash"
        used_query = query
        if not results and fallback_query != query:
            results = _search(fallback_query)
            source = "category_fallback"
            used_query = fallback_query
        if results:
            result = _pick_result(results, used_query)
            base_url = result["urls"]["regular"]
            separator = "&" if "?" in base_url else "?"
            user = result.get("user") or {}
            links = result.get("links") or {}
            attribution_url = links.get("html", "")
            if attribution_url:
                joiner = "&" if "?" in attribution_url else "?"
                attribution_url = (
                    f"{attribution_url}{joiner}utm_source=niyetsen&utm_medium=referral"
                )
            return ImageResult(
                url=f"{base_url}{separator}w=800&h=600&fit=crop&q=82",
                source=source,
                attribution=(
                    f"Photo by {user.get('name')} on Unsplash"
                    if user.get("name") else "Photo on Unsplash"
                ),
                attribution_url=attribution_url,
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s", query, exc)
    return None


def _upload_plan_image(image_bytes: bytes, mime_type: str) -> str | None:
    """Supabase plan-images bucket'a yükle; public URL döner."""
    if not settings.USE_SUPABASE_DB or not settings.SUPABASE_URL:
        return None
    if not settings.SUPABASE_SERVICE_KEY:
        return None
    extension = "jpg" if mime_type == "image/jpeg" else "png"
    path = f"generated/{uuid.uuid4().hex}.{extension}"
    try:
        from supabase import create_client

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        client.storage.from_("plan-images").upload(
            path,
            image_bytes,
            file_options={"content-type": mime_type, "upsert": "false"},
        )
        base = settings.SUPABASE_URL.rstrip("/")
        return f"{base}/storage/v1/object/public/plan-images/{path}"
    except Exception as exc:  # noqa: BLE001
        log.warning("Plan görseli Storage yüklemesi başarısız: %s", exc)
        return None


async def _get_gemini_image(
    *,
    title: str,
    keyword: str,
    city: str = "",
    interests: list[str] | None = None,
    categories: list[str] | None = None,
) -> ImageResult | None:
    from app.core.gemini_client import GeminiUnavailable, generate_image_bytes

    prompt = build_gemini_visual_prompt(
        title=title,
        keyword=keyword,
        city=city,
        interests=interests,
        categories=categories,
    )
    try:
        image_bytes, mime_type = await generate_image_bytes(prompt)
        # Senkron Supabase upload'u event loop'u kilitlemesin.
        public_url = await asyncio.to_thread(_upload_plan_image, image_bytes, mime_type)
        if not public_url:
            log.warning("Nano Banana görseli depolanamadı — Unsplash'a düşülüyor")
            return None
        return ImageResult(
            url=public_url,
            source=_GEMINI_SOURCE,
            attribution=_GEMINI_ATTRIBUTION,
            attribution_url="https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-image",
        )
    except GeminiUnavailable as exc:
        log.warning("Nano Banana atlandı: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("Nano Banana hatası: %s", exc)
        return None


async def get_image_async(
    keyword: str,
    *,
    categories: list[str] | None = None,
    title: str = "",
    city: str = "",
    interests: list[str] | None = None,
    task_type: str = "",
) -> ImageResult:
    """Hibrit görsel: Nano Banana (koşullu) → Unsplash → placeholder."""
    if should_use_gemini_image(
        title=title,
        keyword=keyword,
        task_type=task_type,
        categories=categories,
    ):
        gemini_image = await _get_gemini_image(
            title=title,
            keyword=keyword,
            city=city,
            interests=interests,
            categories=categories,
        )
        if gemini_image is not None:
            return gemini_image

    # _get_unsplash_image senkron httpx.get kullanır (10s'e kadar bloklar);
    # event loop'u kilitlememesi için ayrı thread'de çalıştırılır.
    unsplash_image = await asyncio.to_thread(
        _get_unsplash_image,
        keyword,
        categories=categories,
        title=title,
        city=city,
        interests=interests,
    )
    if unsplash_image is not None:
        return unsplash_image

    query = compose_image_query(
        keyword,
        title=title,
        city=city,
        interests=interests,
        categories=categories,
    )
    fallback_query = category_fallback_query(categories)
    return ImageResult(
        url=_placeholder(query or fallback_query),
        source="placeholder",
    )


def get_image(
    keyword: str,
    *,
    categories: list[str] | None = None,
    title: str = "",
    city: str = "",
    interests: list[str] | None = None,
    task_type: str = "",
) -> ImageResult:
    """Senkron sarmalayıcı (testler + geriye dönük uyumluluk)."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Zaten async bağlamdaysa doğrudan Unsplash (plan_service get_image_async kullanır)
        unsplash_image = _get_unsplash_image(
            keyword,
            categories=categories,
            title=title,
            city=city,
            interests=interests,
        )
        if unsplash_image is not None:
            return unsplash_image
        query = compose_image_query(
            keyword, title=title, city=city, interests=interests, categories=categories
        )
        return ImageResult(url=_placeholder(query), source="placeholder")

    return asyncio.run(
        get_image_async(
            keyword,
            categories=categories,
            title=title,
            city=city,
            interests=interests,
            task_type=task_type,
        )
    )


def get_image_url(keyword: str) -> str:
    """Geriye dönük küçük sözleşme; yeni kod attribution için get_image kullanır."""
    return get_image(keyword).url

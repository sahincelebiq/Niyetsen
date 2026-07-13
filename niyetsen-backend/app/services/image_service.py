"""
Niyetsen — Görsel Servisi
image_keyword → görsel URL. MVP kaynağı Unsplash (lisans temiz).
Cursor notu (v2): Pinterest'e geçilirse SADECE bu dosya değişir; sözleşme
(get_image_url) aynı kalır. ToS/hukuk kontrolü yapılmadan Pinterest'e geçme.
"""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
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


@dataclass(frozen=True)
class ImageResult:
    url: str
    source: str
    attribution: str = ""
    attribution_url: str = ""


def _placeholder(keyword: str) -> str:
    """Anahtar yoksa / arama boş dönerse: deterministik, ücretsiz yer tutucu.
    (Dev ortamında Unsplash anahtarı olmadan da plan ekranı görselli çalışsın.)"""
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


def _search(query: str) -> list[dict]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    resp = httpx.get(
        _UNSPLASH_SEARCH,
        params=_search_params(query),
        headers=_search_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _search_params(query: str) -> dict:
    return {
        "query": query,
        "per_page": 10,
        "orientation": "landscape",
        "order_by": "relevant",
        "content_filter": "high",
    }


def _search_headers() -> dict:
    return {"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"}


async def _search_async(client: httpx.AsyncClient, query: str) -> list[dict]:
    if not settings.UNSPLASH_ACCESS_KEY:
        return []
    resp = await client.get(
        _UNSPLASH_SEARCH,
        params=_search_params(query),
        headers=_search_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _pick_result(results: list[dict], keyword: str) -> dict:
    candidates = results[:5]
    digest = int(hashlib.sha256(keyword.encode()).hexdigest(), 16)
    return candidates[digest % len(candidates)]


def _build_result(results: list[dict], used_query: str, source: str) -> ImageResult:
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


def get_image(keyword: str, *, categories: list[str] | None = None) -> ImageResult:
    query = normalize_image_query(keyword)
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
            return _build_result(results, used_query, source)
    except Exception as e:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s — yer tutucuya düşülüyor", query, e)

    return ImageResult(
        url=_placeholder(query or fallback_query),
        source="placeholder",
    )


async def get_image_async(
    client: httpx.AsyncClient,
    keyword: str,
    *,
    categories: list[str] | None = None,
) -> ImageResult:
    """Async sürüm: plan üretimi görselleri paralel çeker (event loop'u bloklamaz)."""
    query = normalize_image_query(keyword)
    fallback_query = category_fallback_query(categories)
    try:
        results = await _search_async(client, query) if query else []
        source = "unsplash"
        used_query = query
        if not results and fallback_query != query:
            results = await _search_async(client, fallback_query)
            source = "category_fallback"
            used_query = fallback_query
        if results:
            return _build_result(results, used_query, source)
    except Exception as e:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s — yer tutucuya düşülüyor", query, e)

    return ImageResult(
        url=_placeholder(query or fallback_query),
        source="placeholder",
    )


def get_image_url(keyword: str) -> str:
    """Geriye dönük küçük sözleşme; yeni kod attribution için get_image kullanır."""
    return get_image(keyword).url

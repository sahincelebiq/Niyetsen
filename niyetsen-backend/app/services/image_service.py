"""
Niyetsen — Görsel Servisi
image_keyword → görsel URL. MVP kaynağı Unsplash (lisans temiz).
Cursor notu (v2): Pinterest'e geçilirse SADECE bu dosya değişir; sözleşme
(get_image_url) aynı kalır. ToS/hukuk kontrolü yapılmadan Pinterest'e geçme.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

log = logging.getLogger("niyetsen.image")

_UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"


def _placeholder(keyword: str) -> str:
    """Anahtar yoksa / arama boş dönerse: deterministik, ücretsiz yer tutucu.
    (Dev ortamında Unsplash anahtarı olmadan da plan ekranı görselli çalışsın.)"""
    seed = "".join(ch for ch in keyword if ch.isalnum()) or "niyetsen"
    return f"https://picsum.photos/seed/{seed}/800/600"


def get_image_url(keyword: str) -> str:
    keyword = (keyword or "").strip()
    if not keyword:
        return _placeholder("vision")

    if not settings.UNSPLASH_ACCESS_KEY:
        return _placeholder(keyword)

    try:
        resp = httpx.get(
            _UNSPLASH_SEARCH,
            params={"query": keyword, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0]["urls"]["regular"]
    except Exception as e:  # noqa: BLE001
        log.warning("Unsplash hatası (%s): %s — yer tutucuya düşülüyor", keyword, e)

    return _placeholder(keyword)

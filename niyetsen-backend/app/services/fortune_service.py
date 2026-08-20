"""
Niyetsen — Fal Servisi (V2 / FAZ 7)
====================================
Tarot çekimi, kahve/el fotoğrafı yorumu, günlük burç. İkinci (duygusal) system
prompt + knowledge/ RAG bağlamı + Gemini 2.5 Flash (metin ve vision).

İlkeler (philosophy.py): fal KADER değil AYNA; korku satılmaz; her yorum
niyet + en küçük halkaya bağlanır; kriz sinyalinde mistik yorum durur.

Hak sayaçları (docs/niyetsen-03-algoritma.md §5, günlük sıfırlanır):
  el: ücretsiz 1 / premium 3 · kahve: ücretsiz 1 / premium 3 ·
  tarot: herkese 1 (EK YOK) · burç: sınırsız (günlük önbellekli).
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import FORTUNE_DAILY_RIGHTS, TAROT_CARDS_PER_DRAW, settings
from app.core import prompts
from app.core.gemini_client import (
    GeminiUnavailable, generate_json, generate_json_with_images,
)
from app.models.schemas import (
    FortuneRecord, FortuneRightsItem, FortuneRightsResponse,
    HoroscopeResponse, PhotoFortuneResponse, TarotCardResult, TarotDrawResponse,
)
from app.services import rag_service
from app.storage.base import Repository

log = logging.getLogger("niyetsen.fortune")

TAROT_POSITIONS = ["geçmiş", "şimdi", "niyetin yönü"]
_REVERSED_PROBABILITY = 0.3


class FortuneError(ValueError):
    """400 — geçersiz istek (yanlış fotoğraf, eksik profil vb.)."""


class FortuneRightsExhausted(FortuneError):
    """429/409 — günlük hak bitti."""


async def _rag_async(query: str, sources: list[str] | None = None) -> list[str]:
    """RAG sohbeti düşürmez; embedding senkron olduğu için thread'de çalışır."""
    try:
        return await asyncio.to_thread(
            rag_service.retrieve, query, sources=sources
        )
    except Exception:  # noqa: BLE001
        log.warning("Fal RAG atlandı", exc_info=True)
        return []


# ------------------------------------------------------------------
# Tarot destesi: knowledge/tarot.md'den okunur (tek gerçek kaynak);
# dosya yoksa isim listesi fallback'i devreye girer.
# ------------------------------------------------------------------
_TAROT_LINE = re.compile(
    r"^(?P<name>[^(#\n][^(]*?)\s*\((?P<en>[^)]+)\)\s*—\s*(?P<upright>.+?)"
    r"\s*Ters:\s*(?P<reversed>.+?)\s*Niyet:\s*(?P<niyet>.+)$"
)
_FALLBACK_DECK = [
    "Deli", "Büyücü", "Azize", "İmparatoriçe", "İmparator", "Aziz", "Aşıklar",
    "Savaş Arabası", "Güç", "Ermiş", "Kader Çarkı", "Adalet", "Asılan Adam",
    "Ölüm", "Denge", "Şeytan", "Kule", "Yıldız", "Ay", "Güneş", "Mahkeme", "Dünya",
]
_deck_cache: list[dict] | None = None


def _load_deck() -> list[dict]:
    global _deck_cache
    if _deck_cache is not None:
        return _deck_cache
    deck: list[dict] = []
    path = Path(__file__).resolve().parents[2] / "knowledge" / "tarot.md"
    if path.is_file():
        for line in path.read_text().splitlines():
            match = _TAROT_LINE.match(line.strip())
            if match:
                deck.append({
                    "name": match["name"].strip(),
                    "upright": match["upright"].strip(),
                    "reversed": match["reversed"].strip(),
                    "niyet": match["niyet"].strip(),
                })
    if len(deck) < len(_FALLBACK_DECK):
        deck = [
            {"name": name, "upright": "", "reversed": "", "niyet": ""}
            for name in _FALLBACK_DECK
        ]
        log.warning("tarot.md ayrıştırılamadı — fallback deste kullanılıyor")
    _deck_cache = deck
    return deck


# ------------------------------------------------------------------
# Ortak yardımcılar
# ------------------------------------------------------------------
def _local_today(timezone_name: str) -> date:
    try:
        tz = ZoneInfo(timezone_name or "Europe/Istanbul")
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Europe/Istanbul")
    return datetime.now(timezone.utc).astimezone(tz).date()


def _daily_limit(fortune_type: str, is_premium: bool) -> int:
    rights = FORTUNE_DAILY_RIGHTS.get(fortune_type)
    if rights is None:
        return -1  # burç: sınırsız
    return rights["premium"] if is_premium else rights["free"]


def _check_right(
    repository: Repository, user_id: str, fortune_type: str,
    day: date, is_premium: bool,
) -> int:
    """Kalan hakkı döndürür (kullanım öncesi); hak yoksa exception."""
    limit = _daily_limit(fortune_type, is_premium)
    if limit < 0:
        return -1
    used = repository.count_fortunes_for_day(user_id, fortune_type, day)
    if used >= limit:
        raise FortuneRightsExhausted(
            "Bugünün hakkı doldu. Yarın yeni bir gün, yeni bir bakış. 🌙"
            + ("" if is_premium or fortune_type == "tarot"
               else " Premium ile günlük ek hak açılır.")
        )
    return limit - used


def get_rights(
    repository: Repository, user_id: str, timezone_name: str, is_premium: bool,
) -> FortuneRightsResponse:
    day = _local_today(timezone_name)
    rights: dict[str, FortuneRightsItem] = {}
    for fortune_type in ("tarot", "kahve", "el"):
        limit = _daily_limit(fortune_type, is_premium)
        used = repository.count_fortunes_for_day(user_id, fortune_type, day)
        rights[fortune_type] = FortuneRightsItem(
            limit=limit, used=used, remaining=max(0, limit - used),
        )
    rights["burc"] = FortuneRightsItem(limit=-1, used=0, remaining=-1)
    return FortuneRightsResponse(is_premium=is_premium, rights=rights)


def _crisis_signal(text: str) -> bool:
    t = (text or "").casefold()
    return any(m in t for m in (
        "intihar", "kendime zarar", "yaşamak istemiyorum", "olmasam da olur",
        "kendimi öldür",
    ))


# ------------------------------------------------------------------
# faz8.13/2c — Mistik hafıza: fortune_log geçmişi rehber bağlamına girer.
# ------------------------------------------------------------------
def build_mystic_memory(repository: Repository, user_id: str, limit: int = 8) -> str:
    """Kullanıcının geçmiş fallarından kısa hafıza bloğu üretir.

    Rehber bu blokla "geçen haftaki kartında şu görünmüştü — bugün bu
    gerçekleşti mi?" gibi bağlam soruları sorabilir. Hata durumunda boş
    döner — hafıza fal akışını ASLA düşürmez.
    """
    try:
        records = repository.list_fortunes(user_id, limit=limit)
    except Exception:  # noqa: BLE001
        log.warning("Mistik hafıza okunamadı (yoksayıldı)", exc_info=True)
        return ""
    if not records:
        return ""
    lines: list[str] = []
    for record in records:
        result = record.result or {}
        if record.type == "tarot":
            cards = ", ".join(
                f"{c.get('name', '?')}{' (ters)' if c.get('reversed') else ''}"
                for c in result.get("cards", [])
            )
            detail = cards or "kartlar"
        elif record.type == "burc":
            detail = f"{result.get('sign', '')} burcu"
        else:
            detail = ", ".join(result.get("symbols", [])) or "semboller"
        snippet = " ".join(str(result.get("interpretation", "")).split())[:140]
        lines.append(f"- {record.day.isoformat()} {record.type}: {detail} — {snippet}")
    return "MİSTİK HAFIZA (kullanıcının geçmiş falları, en yeniden eskiye):\n" + "\n".join(lines)


# ------------------------------------------------------------------
# faz8.13/2b — Mistik rehber sohbeti (merkez ekran)
# ------------------------------------------------------------------
MYSTIC_CHAT_HISTORY_LIMIT = 12
MYSTIC_CHAT_SOURCES = [
    "tarot", "burclar", "kahve_fali", "el_fali", "motivasyon",
]

MYSTIC_CHAT_SCHEMA = {
    "type": "object",
    "properties": {"reply": {"type": "string"}},
    "required": ["reply"],
}


async def mystic_chat(
    repository: Repository,
    user_id: str,
    *,
    messages: list,                 # ChatMessage listesi
    memory_block: str = "",
) -> str:
    """Mistik rehberle serbest sohbet. Kriz sinyali fal yorumunu durdurur;
    her yanıt istemcide disclaimer ile gösterilir (store uyumu)."""
    last_user = next(
        (m.content for m in reversed(messages) if m.role == "user"), ""
    )
    if prompts.contains_crisis_signal(last_user) or _crisis_signal(last_user):
        return prompts.CRISIS_RESPONSE

    mystic_memory = build_mystic_memory(repository, user_id)
    # Kullanıcı sohbette "fincanımda kuş vardı" / "yaşam çizgim kısa mı" diye
    # sorabiliyor; kaynak listesinde kahve_fali/el_fali yokken rehber bu
    # sorulara sözlüksüz cevap veriyordu.
    rag_chunks = await _rag_async(
        f"mistik {last_user}"[:200],
        sources=MYSTIC_CHAT_SOURCES,
    )
    history_lines = "\n".join(
        f"{'KULLANICI' if m.role == 'user' else 'REHBER'}: {m.content}"
        for m in messages[-MYSTIC_CHAT_HISTORY_LIMIT:]
    )
    contents = "\n\n".join(filter(None, [
        "\n".join(rag_chunks) if rag_chunks else "",
        memory_block,
        mystic_memory,
        f"SOHBET GEÇMİŞİ:\n{history_lines}",
        prompts.MYSTIC_CHAT_JSON_INSTRUCTIONS,
    ]))
    data = await generate_json(
        contents,
        system_instruction=prompts.FORTUNE_SYSTEM_PROMPT,
        model=settings.GEMINI_MODEL,
        response_schema=MYSTIC_CHAT_SCHEMA,
        json_retries=2,
    )
    reply = str(data.get("reply") or "").strip()
    if not reply:
        reply = (
            "Sezgilerim bu an biraz sessiz kaldı 🌙 Sorunu bir daha, "
            "biraz daha açarak sorar mısın?"
        )
    return reply


# ------------------------------------------------------------------
# Tarot
# ------------------------------------------------------------------
async def draw_tarot(
    repository: Repository,
    user_id: str,
    *,
    question: str = "",
    timezone_name: str = "Europe/Istanbul",
    is_premium: bool = False,
    memory_block: str = "",
) -> TarotDrawResponse:
    if _crisis_signal(question):
        raise FortuneError(
            "Şu an fal değil, gerçek destek daha kıymetli. Lütfen güvendiğin "
            "biriyle ya da bir uzmanla konuş; ben de niyetin için buradayım. 🌙"
        )
    day = _local_today(timezone_name)

    existing = repository.get_fortune_for_day(user_id, "tarot", day)
    if existing is not None:
        result = existing.result
        return TarotDrawResponse(
            cards=[TarotCardResult(**c) for c in result.get("cards", [])],
            interpretation=result.get("interpretation", ""),
            already_drawn_today=True,
        )

    _check_right(repository, user_id, "tarot", day, is_premium)

    deck = _load_deck()
    drawn = random.sample(deck, min(TAROT_CARDS_PER_DRAW, len(deck)))
    cards = [
        TarotCardResult(
            name=card["name"],
            position=TAROT_POSITIONS[index % len(TAROT_POSITIONS)],
            reversed=random.random() < _REVERSED_PROBABILITY,
            meaning="",
        )
        for index, card in enumerate(drawn)
    ]
    for card_result, card in zip(cards, drawn):
        card_result.meaning = card["reversed"] if card_result.reversed else card["upright"]

    card_lines = "\n".join(
        f"- {c.position}: {c.name}{' (ters)' if c.reversed else ''} — {c.meaning}"
        for c in cards
    )
    rag_chunks = await _rag_async(
        f"tarot {' '.join(c.name for c in cards)} {question}",
        sources=["tarot", "motivasyon"],
    )
    contents = "\n\n".join(filter(None, [
        "\n".join(rag_chunks) if rag_chunks else "",
        memory_block,
        f"ÇEKİLEN KARTLAR:\n{card_lines}",
        f"KULLANICININ SORUSU: {question}" if question.strip() else "",
        prompts.TAROT_JSON_INSTRUCTIONS,
    ]))

    try:
        data = await generate_json(
            contents,
            system_instruction=prompts.FORTUNE_SYSTEM_PROMPT,
            model=settings.GEMINI_MODEL,
        )
        interpretation = str(data.get("interpretation") or "").strip()
    except GeminiUnavailable:
        interpretation = ""
    if not interpretation:
        # Model yoksa bilgi tabanındaki statik anlamlarla nazik bir yorum kur.
        interpretation = (
            "Kartların bugünkü fısıltısı: "
            + " ".join(f"{c.name}: {c.meaning}" for c in cards if c.meaning)
            + " Bugün atabileceğin en küçük adımı seç ve zincirine bir halka ekle."
        )

    record = FortuneRecord(
        id=str(uuid.uuid4()),
        type="tarot",
        day=day,
        result={
            "cards": [c.model_dump() for c in cards],
            "interpretation": interpretation,
            "question": question[:280],
        },
    )
    repository.save_fortune(user_id, record)
    return TarotDrawResponse(cards=cards, interpretation=interpretation)


# ------------------------------------------------------------------
# Kahve / El fotoğrafı
# ------------------------------------------------------------------
PHOTO_FORTUNE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid_photo": {"type": "boolean"},
        "symbols": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "interpretation": {"type": "string"},
    },
    "required": ["is_valid_photo", "interpretation"],
}

MAX_FORTUNE_PHOTOS = 3  # faz8.13/2d: kahve falında en fazla 3 kare

# Foto falı RAG kaynakları (knowledge/ dosya adlarıyla birebir eşleşir).
FORTUNE_RAG_SOURCE = {"kahve": "kahve_fali", "el": "el_fali"}
FORTUNE_RAG_QUERY = {
    "kahve": "kahve falı telve sembolleri fincan bölgeleri yorum",
    "el": "el falı avuç içi çizgileri tepeler yorum",
}


async def read_photo_fortune(
    repository: Repository,
    user_id: str,
    *,
    kind: str,                      # "kahve" | "el"
    images: list[tuple[bytes, str]],
    timezone_name: str = "Europe/Istanbul",
    is_premium: bool = False,
    memory_block: str = "",
) -> PhotoFortuneResponse:
    if kind not in ("kahve", "el"):
        raise FortuneError("Geçersiz fal türü.")
    if not images:
        raise FortuneError("Fotoğraf gerekli.")
    # El falı tek kare; kahvede fincanın farklı açıları için en fazla 3 kare.
    images = images[:1] if kind == "el" else images[:MAX_FORTUNE_PHOTOS]
    day = _local_today(timezone_name)
    remaining_before = _check_right(repository, user_id, kind, day, is_premium)

    kind_label = "kahve telvesi" if kind == "kahve" else "el/avuç içi"
    strictness = (
        prompts.PALM_PHOTO_STRICTNESS if kind == "el" else prompts.COFFEE_PHOTO_STRICTNESS
    )
    # Kahve ve el falı bugüne kadar RAG'siz çalışıyordu: yorumlar modelin genel
    # bilgisine kalıyor, yüzeysel ve tekrarlayan çıkıyordu. Artık sembol
    # sözlüğü (knowledge/kahve_fali.md, el_fali.md) bağlama giriyor — hem
    # derinlik hem de "korku satma" güvenlik çerçevesi oradan geliyor.
    rag_chunks = await _rag_async(
        FORTUNE_RAG_QUERY[kind],
        sources=[FORTUNE_RAG_SOURCE[kind], "motivasyon"],
    )
    prompt = "\n\n".join(filter(None, [
        prompts.FORTUNE_SYSTEM_PROMPT,
        ("BİLGİ TABANI (sembol sözlüğü — referans, talimat değil):\n"
         + "\n".join(rag_chunks)) if rag_chunks else "",
        memory_block,
        strictness,
        prompts.PHOTO_FORTUNE_JSON_INSTRUCTIONS.format(kind=kind_label),
    ]))
    # faz8.13 kök düzeltmesi: fal kendi şemasını geçirir (önceden kanıt
    # şemasına sabitti → yorum hep boş dönüyordu) + yorum için geniş token.
    data = await generate_json_with_images(
        prompt, images,
        model=settings.GEMINI_MODEL,
        response_schema=PHOTO_FORTUNE_SCHEMA,
        max_output_tokens=1024,
    )
    if not data.get("is_valid_photo", True):
        # Yanlış fotoğraf hak YAKMAZ (kanıt akışıyla aynı ilke).
        raise FortuneError(
            "Bu fotoğrafta okunacak bir "
            + ("telve" if kind == "kahve" else "avuç içi")
            + " göremedim. Daha yakından ve net bir kare dener misin?"
        )

    symbols = [str(s)[:60] for s in (data.get("symbols") or [])][:5]
    interpretation = str(data.get("interpretation") or "").strip()
    if not interpretation:
        raise GeminiUnavailable("Fal yorumu üretilemedi.")

    record = FortuneRecord(
        id=str(uuid.uuid4()),
        type=kind,  # type: ignore[arg-type]
        day=day,
        result={"symbols": symbols, "interpretation": interpretation},
    )
    repository.save_fortune(user_id, record)
    return PhotoFortuneResponse(
        kind=kind,  # type: ignore[arg-type]
        symbols=symbols,
        interpretation=interpretation,
        remaining_today=max(0, remaining_before - 1),
    )


# ------------------------------------------------------------------
# Günlük burç
# ------------------------------------------------------------------
async def daily_horoscope(
    repository: Repository,
    user_id: str,
    *,
    sign: str,
    timezone_name: str = "Europe/Istanbul",
    memory_block: str = "",
    period: str = "daily",          # daily | weekly (Dalga 3)
) -> HoroscopeResponse:
    if not sign:
        raise FortuneError(
            "Burcunu bilmem için doğum tarihine ihtiyacım var — profilinden ekleyebilirsin."
        )
    if period not in ("daily", "weekly"):
        raise FortuneError("Geçersiz dönem — daily veya weekly.")
    today = _local_today(timezone_name)
    # Haftalık görünüm haftanın pazartesisine çapalanır: hafta boyunca tek
    # üretim (maliyet) + kararlı önbellek anahtarı.
    day = today - timedelta(days=today.weekday()) if period == "weekly" else today

    cached = repository.get_fortune_for_day(user_id, "burc", day)
    if (
        cached is not None
        and cached.result.get("sign") == sign
        and cached.result.get("period", "daily") == period
    ):
        return HoroscopeResponse(
            sign=sign, day=day,
            interpretation=cached.result.get("interpretation", ""),
        )

    rag_chunks = await _rag_async(f"{sign} burcu", sources=["burclar"])
    period_note = (
        "Bu HAFTALIK bir yorum: haftanın genel enerjisi + haftaya yayılan "
        "2-3 küçük adım öner." if period == "weekly" else ""
    )
    contents = "\n\n".join(filter(None, [
        "\n".join(rag_chunks) if rag_chunks else "",
        memory_block,
        period_note,
        prompts.HOROSCOPE_JSON_INSTRUCTIONS.format(sign=sign, day=day.isoformat()),
    ]))
    try:
        data = await generate_json(
            contents,
            system_instruction=prompts.FORTUNE_SYSTEM_PROMPT,
            model=settings.GEMINI_MODEL,
        )
        interpretation = str(data.get("interpretation") or "").strip()
    except GeminiUnavailable:
        interpretation = ""
    if not interpretation:
        chunk = rag_chunks[0] if rag_chunks else ""
        interpretation = (
            f"{sign} için bugünün notu: {chunk.splitlines()[-1] if chunk else ''} "
            "Bugün zincirine tek bir halka eklemen yeterli."
        ).strip()

    record = FortuneRecord(
        id=str(uuid.uuid4()),
        type="burc",
        day=day,
        result={"sign": sign, "interpretation": interpretation, "period": period},
    )
    repository.save_fortune(user_id, record)
    return HoroscopeResponse(sign=sign, day=day, interpretation=interpretation)

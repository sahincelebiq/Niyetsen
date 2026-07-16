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

import logging
import random
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import FORTUNE_DAILY_RIGHTS, TAROT_CARDS_PER_DRAW, settings
from app.core import prompts
from app.core.gemini_client import (
    GeminiUnavailable, generate_json, generate_json_with_image,
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
    rag_chunks = rag_service.retrieve(
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
async def read_photo_fortune(
    repository: Repository,
    user_id: str,
    *,
    kind: str,                      # "kahve" | "el"
    image_bytes: bytes,
    mime_type: str,
    timezone_name: str = "Europe/Istanbul",
    is_premium: bool = False,
    memory_block: str = "",
) -> PhotoFortuneResponse:
    if kind not in ("kahve", "el"):
        raise FortuneError("Geçersiz fal türü.")
    day = _local_today(timezone_name)
    remaining_before = _check_right(repository, user_id, kind, day, is_premium)

    kind_label = "kahve telvesi" if kind == "kahve" else "el/avuç içi"
    prompt = (
        prompts.FORTUNE_SYSTEM_PROMPT
        + "\n\n" + memory_block
        + "\n\n" + prompts.PHOTO_FORTUNE_JSON_INSTRUCTIONS.format(kind=kind_label)
    )
    data = await generate_json_with_image(
        prompt, image_bytes, mime_type, model=settings.GEMINI_MODEL
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
) -> HoroscopeResponse:
    if not sign:
        raise FortuneError(
            "Burcunu bilmem için doğum tarihine ihtiyacım var — profilinden ekleyebilirsin."
        )
    day = _local_today(timezone_name)

    cached = repository.get_fortune_for_day(user_id, "burc", day)
    if cached is not None and cached.result.get("sign") == sign:
        return HoroscopeResponse(
            sign=sign, day=day,
            interpretation=cached.result.get("interpretation", ""),
        )

    rag_chunks = rag_service.retrieve(f"{sign} burcu", sources=["burclar"])
    contents = "\n\n".join(filter(None, [
        "\n".join(rag_chunks) if rag_chunks else "",
        memory_block,
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
        result={"sign": sign, "interpretation": interpretation},
    )
    repository.save_fortune(user_id, record)
    return HoroscopeResponse(sign=sign, day=day, interpretation=interpretation)

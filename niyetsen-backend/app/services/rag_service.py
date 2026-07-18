"""
Niyetsen — RAG Servisi (V2 fal modülü bilgi tabanı)
====================================================
knowledge/*.md → başlık bazlı chunk → Gemini embedding → kosinüs benzerliği.

Tasarım kararları (MASTER_PLAN §1.9 maliyet + Railway kısıtları):
- Varsayılan backend IN-MEMORY: embedding'ler süreç içinde önbelleklenir,
  ekstra bağımlılık/disk yok. Railway'in geçici dosya sistemiyle uyumlu.
- Chroma OPSİYONEL: `RAG_BACKEND=chroma` + `pip install chromadb` ile
  `chroma_db/` dizinine kalıcılaşır (lokalde). Kod yolu aynı kalır.
- Gemini embedding yoksa/başarısızsa KEYWORD fallback devreye girer —
  testler ve anahtar olmayan ortamlar ağsız çalışır.
- RAG içeriği prompt'a HER ZAMAN etiketli CONTEXT bloğuyla girer
  (prompt_builder.build_context) — kullanıcı mesajıyla asla karışmaz.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.config import settings

log = logging.getLogger("niyetsen.rag")

# knowledge/ backend kökünde yaşar (Railway root = /niyetsen-backend olduğu
# için repo köküne konursa prod'a deploy OLMAZ).
_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
# Embedding disk önbelleği (Dalga 3): süreç yeniden başlasa bile aynı chunk
# için Gemini embedding API'sine tekrar gidilmez (maliyet + soğuk başlangıç).
# Dosya gitignore'da; içerik değişirse anahtar (hash) değişir, otomatik tazelenir.
_EMBED_CACHE_PATH = Path(__file__).resolve().parents[2] / ".rag_embed_cache.json"

_CHUNK_MAX_CHARS = 900


@dataclass
class _Chunk:
    source: str          # dosya adı (tarot / burclar / ...)
    heading: str
    text: str
    embedding: list[float] | None = None
    tokens: set[str] = field(default_factory=set)


_chunks: list[_Chunk] | None = None
_lock = Lock()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9çğıöşü]+", _normalize(text)) if len(t) > 2}


def _split_markdown(source: str, body: str) -> list[_Chunk]:
    """Başlıklara göre böl; uzun bölümleri paragraf sınırından parçala."""
    chunks: list[_Chunk] = []
    heading = source
    buf: list[str] = []

    def flush() -> None:
        text = "\n".join(buf).strip()
        buf.clear()
        if not text:
            return
        # Uzun bölümler paragraf paragraf _CHUNK_MAX_CHARS'a bölünür.
        current = ""
        for para in text.split("\n"):
            if current and len(current) + len(para) + 1 > _CHUNK_MAX_CHARS:
                chunks.append(_Chunk(source, heading, current.strip()))
                current = para
            else:
                current = f"{current}\n{para}" if current else para
        if current.strip():
            chunks.append(_Chunk(source, heading, current.strip()))

    for line in body.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("# ").strip() or heading
            continue
        buf.append(line)
    flush()
    for chunk in chunks:
        chunk.tokens = _tokenize(f"{chunk.heading} {chunk.text}")
    return chunks


def _load_chunks() -> list[_Chunk]:
    global _chunks
    with _lock:
        if _chunks is not None:
            return _chunks
        chunks: list[_Chunk] = []
        if _KNOWLEDGE_DIR.is_dir():
            for path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
                try:
                    chunks.extend(_split_markdown(path.stem, path.read_text()))
                except OSError as exc:
                    log.warning("Bilgi tabanı okunamadı (%s): %s", path.name, exc)
        else:
            log.warning("knowledge/ dizini yok: %s — RAG boş çalışacak", _KNOWLEDGE_DIR)
        _chunks = chunks
        log.info("RAG bilgi tabanı: %d chunk yüklendi", len(chunks))
        return chunks


def _embed(texts: list[str]) -> list[list[float]] | None:
    """Gemini embedding; anahtar yoksa veya hata olursa None (keyword fallback)."""
    if not settings.GEMINI_API_KEY or not settings.RAG_EMBEDDINGS_ENABLED:
        return None
    try:
        from app.core.gemini_client import get_client

        client = get_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBED_MODEL,
            contents=texts,
        )
        return [list(e.values) for e in result.embeddings]
    except Exception as exc:  # noqa: BLE001 — RAG asla isteği düşürmez
        log.warning("Embedding atlandı (%s) — keyword fallback", exc)
        return None


def _cache_key(chunk: _Chunk) -> str:
    raw = f"{settings.GEMINI_EMBED_MODEL}:{chunk.heading}:{chunk.text}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_embed_cache() -> dict[str, list[float]]:
    try:
        if _EMBED_CACHE_PATH.is_file():
            return json.loads(_EMBED_CACHE_PATH.read_text())
    except (OSError, ValueError) as exc:
        log.warning("Embedding önbelleği okunamadı: %s", exc)
    return {}


def _save_embed_cache(cache: dict[str, list[float]]) -> None:
    try:
        _EMBED_CACHE_PATH.write_text(json.dumps(cache))
    except OSError as exc:  # disk yazılamazsa RAG yine çalışır (yalnız cache yok)
        log.warning("Embedding önbelleği yazılamadı: %s", exc)


def _ensure_embeddings(chunks: list[_Chunk]) -> bool:
    pending = [c for c in chunks if c.embedding is None]
    if not pending:
        return True

    # 1) Disk önbelleğinden doldur (API çağrısı yok).
    cache = _load_embed_cache()
    still_pending: list[_Chunk] = []
    with _lock:
        for chunk in pending:
            cached = cache.get(_cache_key(chunk))
            if cached:
                chunk.embedding = cached
            else:
                still_pending.append(chunk)
    if not still_pending:
        return True

    # 2) Kalanlar için Gemini embedding + önbelleğe yaz.
    vectors = _embed([f"{c.heading}\n{c.text}" for c in still_pending])
    if vectors is None or len(vectors) != len(still_pending):
        return all(c.embedding is not None for c in chunks)
    with _lock:
        for chunk, vector in zip(still_pending, vectors):
            chunk.embedding = vector
            cache[_cache_key(chunk)] = vector
    _save_embed_cache(cache)
    return True


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def _keyword_scores(query: str, chunks: list[_Chunk]) -> list[tuple[float, _Chunk]]:
    query_tokens = _tokenize(query)
    scored: list[tuple[float, _Chunk]] = []
    for chunk in chunks:
        if not query_tokens:
            break
        overlap = len(query_tokens & chunk.tokens)
        if overlap:
            scored.append((overlap / len(query_tokens), chunk))
    return scored


def retrieve(
    query: str,
    *,
    k: int | None = None,
    sources: list[str] | None = None,
) -> list[str]:
    """
    Sorguya en yakın bilgi tabanı parçalarını döndürür (etiketli metin).
    sources: yalnız belirli dosyalarla sınırla (ör. ["tarot"], ["burclar"]).
    Hata durumunda BOŞ liste döner — çağıran akış asla kırılmaz.
    """
    if not settings.RAG_ENABLED:
        return []
    top_k = k or settings.RAG_TOP_K
    chunks = _load_chunks()
    if sources:
        chunks = [c for c in chunks if c.source in sources]
    if not chunks or not query.strip():
        return []

    scored: list[tuple[float, _Chunk]]
    if _ensure_embeddings(chunks):
        query_vec = _embed([query])
        if query_vec:
            scored = [
                (_cosine(query_vec[0], c.embedding), c)
                for c in chunks
                if c.embedding is not None
            ]
        else:
            scored = _keyword_scores(query, chunks)
    else:
        scored = _keyword_scores(query, chunks)

    scored.sort(key=lambda item: -item[0])
    return [
        f"[{c.source} · {c.heading}]\n{c.text}"
        for score, c in scored[:top_k]
        if score > 0
    ]


# Sohbet için kaynak seçimi: rehber varsayılan olarak felsefe + motivasyon +
# kişisel gelişim (atomik alışkanlıklar) bilgisiyle konuşur; kullanıcı mistik
# konu açarsa ilgili kaynaklar da eklenir.
_CHAT_DEFAULT_SOURCES = ["felsefe", "motivasyon", "atomik_aliskanliklar", "senaryolar"]
_MYSTIC_TRIGGERS = {
    "tarot": ["tarot"],
    "burclar": ["burç", "burc", "astro", "yükselen", "yukselen", "horoskop"],
}


def retrieve_for_chat(message: str, *, k: int | None = None) -> list[str]:
    """Ana /chat akışı için bağlama göre bilgi tabanı parçaları."""
    sources = list(_CHAT_DEFAULT_SOURCES)
    normalized = _normalize(message)
    for source, triggers in _MYSTIC_TRIGGERS.items():
        if any(_normalize(t) in normalized for t in triggers):
            sources.append(source)
    return retrieve(message, k=k or settings.RAG_TOP_K, sources=sources)


def reset_cache() -> None:
    """Testler için: chunk + embedding önbelleğini sıfırla."""
    global _chunks
    with _lock:
        _chunks = None

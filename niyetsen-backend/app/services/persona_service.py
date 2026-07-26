"""
İdol Modu — Persona katmanı (Dalga 4.3).
==========================================
İki kaynaklı tasarım (bilinçli):
  1) SUPABASE (asıl kaynak): idol_personas + persona_chunks. Yeni idol eklemek
     deploy gerektirmez; script/panel besler, uygulama anında görür.
  2) knowledge/personas/*.json + idoller.md (tohum + çevrimdışı yedek):
     DB erişilemezse veya USE_SUPABASE_DB kapalıysa buradan okunur.

Hukuki çerçeve kodda zorlanır: dışarıya dönen her pakette `path_name`
(felsefe adı) ana etikettir; kişi adı yalnız `source_note` içinde
"…ilham alır; bağlantılı değildir" kalıbıyla görünür.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.config import settings

log = logging.getLogger("niyetsen.persona")

_PERSONA_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "personas"
_CHUNK_TARGET_WORDS = 120        # 80-150 kelime hedefi (RAG chunk standardı)
_DISCLAIMER_SUFFIX = "kendisiyle bağlantılı değildir."


@dataclass
class Persona:
    slug: str
    path_name: str
    tagline: str = ""
    category: str = "genel"
    inspired_by: str = ""
    source_note: str = ""
    dossier: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def public_dict(self) -> dict:
        """Arayüze giden güvenli gösterim (kişi adı yalnız kaynak notunda)."""
        return {
            "slug": self.slug,
            "name": self.path_name,
            "tagline": self.tagline,
            "category": self.category,
            "philosophy": str(self.dossier.get("mindset") or self.dossier.get("why_important") or "")[:600],
            "source_note": self.source_note,
        }


_cache: list[Persona] | None = None
_lock = Lock()


def _ensure_source_note(data: dict) -> str:
    note = (data.get("source_note") or "").strip()
    inspired = (data.get("inspired_by") or "").strip()
    if note:
        # Disclaimer eksikse zorla ekle (store/hukuk güvencesi).
        return note if _DISCLAIMER_SUFFIX in note else f"{note.rstrip('.')}; {_DISCLAIMER_SUFFIX}"
    if inspired:
        return (
            f"Bu yol {inspired} kişisinin kamuya açık yaklaşımından ilham alır; "
            f"{_DISCLAIMER_SUFFIX}"
        )
    return ""


def _persona_from_dict(data: dict) -> Persona:
    return Persona(
        slug=str(data.get("slug") or "").strip(),
        path_name=str(data.get("path_name") or "").strip(),
        tagline=str(data.get("tagline") or "").strip(),
        category=str(data.get("category") or "genel").strip(),
        inspired_by=str(data.get("inspired_by") or "").strip(),
        source_note=_ensure_source_note(data),
        dossier=data.get("dossier") or {},
        tags=[str(t) for t in (data.get("tags") or [])],
    )


def _load_from_files() -> list[Persona]:
    personas: list[Persona] = []
    if not _PERSONA_DIR.is_dir():
        return personas
    for path in sorted(_PERSONA_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            personas.append(_persona_from_dict(json.loads(path.read_text())))
        except (OSError, ValueError) as exc:
            log.warning("Persona dosyası okunamadı (%s): %s", path.name, exc)
    return [p for p in personas if p.slug and p.path_name]


def _load_from_db() -> list[Persona]:
    if not settings.USE_SUPABASE_DB:
        return []
    try:
        from app.storage.repository import repo

        rows = repo.list_idol_personas()  # type: ignore[attr-defined]
        return [_persona_from_dict(row) for row in rows]
    except Exception as exc:  # noqa: BLE001 — DB yoksa dosyaya düşülür
        log.info("Persona DB okunamadı, dosya kaynağına düşülüyor: %s", exc)
        return []


def list_personas(force_reload: bool = False) -> list[Persona]:
    """DB öncelikli, dosya yedekli persona listesi (süreç içi önbellekli)."""
    global _cache
    with _lock:
        if _cache is not None and not force_reload:
            return _cache
    personas = _load_from_db() or _load_from_files()
    with _lock:
        _cache = personas
    return personas


def get_persona(slug_or_name: str) -> Persona | None:
    needle = slug_or_name.strip().casefold()
    for persona in list_personas():
        if needle in (persona.slug.casefold(), persona.path_name.casefold()):
            return persona
    return None


def match_persona(text: str) -> Persona | None:
    """Kullanıcı metninde geçen kişi/yol adını en uygun persona'ya eşler.

    "McConaughey gibi olmak istiyorum" → Greenlights Yolu.
    """
    haystack = text.casefold()
    best: tuple[int, Persona] | None = None
    for persona in list_personas():
        score = 0
        if persona.path_name.casefold() in haystack:
            score += 3
        if persona.inspired_by and persona.inspired_by.casefold() in haystack:
            score += 3
        # Soyad eşleşmesi (tek kelime, ≥4 harf) — "mcconaughey gibi"
        for part in persona.inspired_by.split():
            if len(part) >= 4 and part.casefold() in haystack:
                score += 2
        score += sum(1 for tag in persona.tags if tag.casefold() in haystack)
        if score and (best is None or score > best[0]):
            best = (score, persona)
    return best[1] if best else None


def build_chunks(persona: Persona) -> list[dict]:
    """Dossier'ı 80-150 kelimelik RAG bloklarına böler (ingest + retrieval)."""
    chunks: list[dict] = []
    for section, value in (persona.dossier or {}).items():
        if section == "sources":
            continue
        if isinstance(value, list):
            text = " ".join(str(item) for item in value)
        else:
            text = str(value or "")
        words = text.split()
        if not words:
            continue
        for index in range(0, len(words), _CHUNK_TARGET_WORDS):
            block = " ".join(words[index:index + _CHUNK_TARGET_WORDS])
            chunks.append({
                "persona_slug": persona.slug,
                "section": section,
                "chunk_index": len(chunks),
                "text": f"[{persona.path_name} · {section}] {block}",
            })
    return chunks


def context_for(persona: Persona, *, max_chunks: int = 6) -> str:
    """Plan/sohbet promptuna girecek etiketli bağlam bloğu."""
    priority = [
        "mindset", "core_beliefs", "habits", "daily_routine",
        "sports_or_physical_practice", "reading_profile",
        "books_read_or_recommended", "lessons_for_users",
    ]
    chunks = build_chunks(persona)
    chunks.sort(key=lambda c: priority.index(c["section"]) if c["section"] in priority else 99)
    body = "\n".join(chunk["text"] for chunk in chunks[:max_chunks])
    return (
        f"FELSEFE YOLU BAĞLAMI — {persona.path_name} ({persona.tagline})\n"
        f"{body}\n"
        f"NOT: {persona.source_note} Görev başlıklarında kişi adı KULLANMA; "
        f"görevler bu yolun pratiklerinden türesin (taklit değil, tercüme)."
    )


def reset_cache() -> None:
    global _cache
    with _lock:
        _cache = None

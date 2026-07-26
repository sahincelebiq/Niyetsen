"""
Dalga 4.2 — Felsefe Yolları listesi (İdol Modu arayüzü için).
knowledge/idoller.md tek gerçek kaynaktır; bu servis onu yapılandırılmış
listeye çevirir. Yeni yol eklemek = yalnız markdown'a bölüm eklemek
(kod değişikliği gerekmez — Cursor/Şahin doğrudan besleyebilir).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from threading import Lock

from pydantic import BaseModel

log = logging.getLogger("niyetsen.paths")

_IDOL_FILE = Path(__file__).resolve().parents[2] / "knowledge" / "idoller.md"
# "## Greenlights Yolu — engeli fırsata çevirmek" → isim + slogan
_HEADING = re.compile(r"^##\s+(?P<name>[^—\n]+?)\s*—\s*(?P<tagline>.+)$")


class PhilosophyPath(BaseModel):
    name: str          # "Greenlights Yolu"
    tagline: str       # "engeli fırsata çevirmek"
    philosophy: str    # FELSEFE paragrafı (rehber tonu satırına kadar)
    source_note: str   # "...den ilham alır" cümlesi (hukuki çerçeve)


_cache: list[PhilosophyPath] | None = None
_lock = Lock()


def _extract_source_note(text: str) -> str:
    match = re.search(r"Bu yol[^.]*ilham alır[^.]*\.", text)
    return match.group(0).strip() if match else ""


def list_paths() -> list[PhilosophyPath]:
    global _cache
    with _lock:
        if _cache is not None:
            return _cache

    # Dalga 4.3: persona deposu (Supabase/JSON dossier) ÖNCELİKLİ; markdown
    # yolları da listeye eklenir (aynı ada sahip olan dossier sürümü kazanır).
    persona_paths: list[PhilosophyPath] = []
    try:
        from app.services import persona_service

        persona_paths = [
            PhilosophyPath(
                name=p.path_name,
                tagline=p.tagline,
                philosophy=str(
                    p.dossier.get("mindset") or p.dossier.get("why_important") or ""
                )[:600],
                source_note=p.source_note,
            )
            for p in persona_service.list_personas()
        ]
    except Exception as exc:  # noqa: BLE001 — markdown yedeğe düş
        log.info("Persona deposu okunamadı, idoller.md kullanılacak: %s", exc)

    with _lock:
        paths: list[PhilosophyPath] = []
        if _IDOL_FILE.is_file():
            sections = re.split(r"^## ", _IDOL_FILE.read_text(), flags=re.M)[1:]
            for section in sections:
                lines = section.splitlines()
                m = re.match(r"^(?P<name>[^—]+?)\s*—\s*(?P<tagline>.+)$", lines[0])
                if not m:
                    continue
                body = "\n".join(lines[1:])
                fels = re.search(r"FELSEFE:\s*(.+?)(?:\nRehber tonu:|\nPRATİK:)", body, re.S)
                philosophy = " ".join((fels.group(1) if fels else "").split())
                paths.append(PhilosophyPath(
                    name=m["name"].strip(),
                    tagline=m["tagline"].strip(),
                    philosophy=philosophy[:600],
                    source_note=_extract_source_note(philosophy),
                ))
        # Birleştirme: dossier sürümü aynı adlı markdown yolunu EZER.
        dossier_names = {p.name.casefold() for p in persona_paths}
        merged = persona_paths + [
            p for p in paths if p.name.casefold() not in dossier_names
        ]
        if not merged:
            log.warning("Persona/markdown kaynağı boş — yol listesi boş dönecek")
        _cache = merged
        return merged


def reset_cache() -> None:
    global _cache
    with _lock:
        _cache = None

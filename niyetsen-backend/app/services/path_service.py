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
        if not paths:
            log.warning("idoller.md okunamadı veya boş — yol listesi boş dönecek")
        _cache = paths
        return paths


def reset_cache() -> None:
    global _cache
    with _lock:
        _cache = None

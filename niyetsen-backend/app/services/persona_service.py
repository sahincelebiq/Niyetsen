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
from datetime import date
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.models.schemas import ChatRequest, ChatResponse, Task
    from app.storage.base import Repository

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

    # FAZ 8.9: İdol detay ekranı için zengin ama GÜVENLİ görünüm.
    # YASAL KURAL değişmez: kişi adı yalnız source_note'ta; public_quotes
    # bilerek DIŞARIDA (alıntı = kişiye atıf, gri alanı açar).
    _DETAIL_FIELDS = (
        "core_beliefs", "mindset", "habits", "daily_routine",
        "decision_style", "failure_and_recovery", "lessons_for_users", "books",
    )

    def detail_dict(self) -> dict:
        detail = self.public_dict()
        detail["sections"] = [
            {"key": key, "value": self.dossier[key]}
            for key in self._DETAIL_FIELDS
            if self.dossier.get(key)
        ]
        return detail


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
    """DB + dosya birleşimi (slug tekil). Yeni JSON, eski DB satırında kaybolmaz."""
    global _cache
    with _lock:
        if _cache is not None and not force_reload:
            return _cache
    by_slug: dict[str, Persona] = {
        persona.slug: persona for persona in _load_from_files()
    }
    for persona in _load_from_db():
        by_slug[persona.slug] = persona
    personas = sorted(by_slug.values(), key=lambda item: item.path_name.casefold())
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


_PATH_CATEGORIES: dict[str, list[str]] = {
    "anlam": ["Özsaygı"],
    "irade": ["İrade"],
    "sanat": ["Özgüven"],
    "spor": ["İrade"],
    "düşünce": ["Disiplin"],
    "genel": ["İstikrar"],
}


def seed_today_lessons(
    repo: "Repository",
    user_id: str,
    persona: Persona,
    *,
    today: date | None = None,
    max_lessons: int = 2,
) -> list["Task"]:
    """Yolun derslerini bugünün planına ekler (aynı başlık varsa atlar)."""
    from app.services import plan_edit_service

    today = today or date.today()
    lessons = [
        str(item).strip()
        for item in (persona.dossier.get("lessons_for_users") or [])
        if str(item).strip()
    ]
    categories = _PATH_CATEGORIES.get(persona.category, ["İstikrar"])
    existing = {task.title.casefold() for task in repo.list_tasks_for_date(user_id, today)}
    if any(lesson.casefold() in existing for lesson in lessons):
        return []
    added: list[Task] = []
    for lesson in lessons:
        if len(added) >= max_lessons:
            break
        if lesson.casefold() in existing:
            continue
        try:
            task = plan_edit_service.add_task(
                repo,
                user_id,
                today,
                title=lesson[:120],
                categories=categories,  # type: ignore[arg-type]
                tiny_version=lesson[:80],
                duration_min=10,
                today=today,
            )
        except plan_edit_service.PlanEditError:
            break
        added.append(task)
        existing.add(task.title.casefold())
    return added


def apply_path_after_chat(
    repo: "Repository",
    user_id: str,
    req: "ChatRequest",
    response: "ChatResponse",
    *,
    today: date | None = None,
) -> str | None:
    """'Bu yolla sohbete başla' sonrası: niyet + bugünün görevleri + plan CTA."""
    if getattr(response, "crisis", False):
        return None
    last = next(
        (message.content for message in reversed(req.messages) if message.role == "user"),
        "",
    )
    persona = match_persona(last)
    if persona is None:
        return None
    if persona.path_name not in response.collected.interests:
        response.collected.interests.append(persona.path_name)

    profile = repo.get_profile(user_id)
    if today is None:
        from app.services.project_service import _user_local_today

        today = _user_local_today(getattr(profile, "timezone", None) or "Europe/Istanbul")

    if repo.get_plan(user_id) is None:
        from app.services.intent_service import _fill_intent_defaults

        response.collected = _fill_intent_defaults(response.collected)
        if not response.collected.duration_days:
            response.collected.duration_days = 365
        response.ready_for_plan = True
        return (
            f"{persona.path_name} niyetine işlendi. "
            "Planı oluşturunca görevler bu yoldan türeyecek; hatırlatman saatinde gelecek."
        )

    added = seed_today_lessons(repo, user_id, persona, today=today)
    if added:
        titles = ", ".join(task.title for task in added)
        return (
            f"{persona.path_name} bugünün planına işlendi: {titles}. "
            "Hatırlatman saatinde bu görevler için bildirim gelir."
        )
    return (
        f"{persona.path_name} niyetinde duruyor. "
        "Bugünün görevleri zaten bu yoldan; hatırlatman saatinde gelir."
    )


def paths_in_interests(interests: list[str]) -> list[str]:
    names: list[str] = []
    for item in interests:
        if not item:
            continue
        persona = get_persona(item)
        if persona and persona.path_name not in names:
            names.append(persona.path_name)
    return names


def active_path_name(repo: "Repository", user_id: str) -> str:
    active = repo.get_active_intent(user_id)
    if not active:
        return ""
    names = paths_in_interests(active[0].interests)
    return names[0] if names else ""


def activate_path(
    repo: "Repository",
    user_id: str,
    slug: str,
    *,
    today: date | None = None,
) -> dict:
    """Yolu niyete yazar, varsa bugünün derslerini eker, o günün bonusunu yol tadında sunar."""
    from app.models.schemas import CollectedIntent
    from app.services import bonus_service

    persona = get_persona(slug)
    if persona is None:
        raise KeyError(slug)

    today = today or date.today()
    active = repo.get_active_intent(user_id)
    if active:
        collected, ready = active
    else:
        collected = CollectedIntent()
        ready = False
    if persona.path_name not in collected.interests:
        collected.interests.append(persona.path_name)
    duration = collected.duration_days or 365
    repo.save_intent(user_id, collected, duration, ready_for_plan=ready)

    tasks_seeded: list[str] = []
    if repo.get_plan(user_id) is not None:
        added = seed_today_lessons(repo, user_id, persona, today=today)
        tasks_seeded = [task.title for task in added]

    bonus = bonus_service.offer_for_day(
        repo, user_id, today, path_name=persona.path_name
    )
    return {
        "path": persona.public_dict(),
        "activated": True,
        "tasks_seeded": tasks_seeded,
        "bonus": bonus.model_dump(),
    }

#!/usr/bin/env python3
"""
İdol Modu persona besleme (Dalga 4.3).
=======================================
knowledge/personas/*.json → Supabase (idol_personas + persona_chunks).

Kullanım:
    cd niyetsen-backend
    python -m scripts.ingest_personas            # hepsini yükle
    python -m scripts.ingest_personas --dry-run  # yalnız doğrula, yazma

Yeni idol eklemek: knowledge/personas/ altına JSON koy → bu scripti çalıştır.
Deploy GEREKMEZ; uygulama personayı bir sonraki istekte görür.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from app.services import persona_service  # noqa: E402

REQUIRED_DOSSIER_FIELDS = (
    "why_important", "core_beliefs", "mindset", "habits", "daily_routine",
    "reading_profile", "lessons_for_users", "sources",
)


def validate(persona: persona_service.Persona) -> list[str]:
    problems: list[str] = []
    if not persona.slug or not persona.path_name:
        problems.append("slug/path_name boş")
    if "yol" not in persona.path_name.casefold():
        problems.append(f"{persona.path_name}: paket adı felsefe adı olmalı ('… Yolu')")
    if persona.inspired_by and persona.inspired_by.casefold() in persona.path_name.casefold():
        problems.append(f"{persona.path_name}: paket adında KİŞİ ADI olamaz (hukuki risk)")
    if "bağlantılı değildir" not in persona.source_note:
        problems.append(f"{persona.path_name}: source_note disclaimer eksik")
    missing = [f for f in REQUIRED_DOSSIER_FIELDS if not persona.dossier.get(f)]
    if missing:
        problems.append(f"{persona.path_name}: eksik alanlar → {', '.join(missing)}")
    sources = persona.dossier.get("sources") or []
    if len(sources) < 2:
        problems.append(f"{persona.path_name}: en az 2 kaynak gerekli")
    return problems


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    personas = persona_service._load_from_files()  # dosya kaynağı (tohum)
    if not personas:
        print("knowledge/personas/ boş — yapılacak iş yok.")
        return 0

    all_problems: list[str] = []
    for persona in personas:
        all_problems.extend(validate(persona))

    if all_problems:
        print("❌ Doğrulama hataları:")
        for problem in all_problems:
            print(f"  - {problem}")
        return 1

    print(f"✅ {len(personas)} persona doğrulandı.")
    for persona in personas:
        chunks = persona_service.build_chunks(persona)
        print(f"  · {persona.path_name:24s} {len(chunks):3d} chunk  ({persona.category})")
        if dry_run:
            continue
        try:
            from app.storage.repository import repo

            repo.upsert_idol_persona(  # type: ignore[attr-defined]
                {
                    "slug": persona.slug,
                    "path_name": persona.path_name,
                    "tagline": persona.tagline,
                    "category": persona.category,
                    "inspired_by": persona.inspired_by,
                    "source_note": persona.source_note,
                    "dossier": persona.dossier,
                    "tags": persona.tags,
                },
                chunks,
            )
        except NotImplementedError:
            print("    (bellek-içi repo — DB yazımı atlandı; USE_SUPABASE_DB=true gerekir)")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"    HATA: {exc}")
            return 1

    print("dry-run tamam." if dry_run else "Supabase'e yazıldı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

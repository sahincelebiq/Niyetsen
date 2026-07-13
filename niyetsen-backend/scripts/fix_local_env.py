#!/usr/bin/env python3
"""Bozuk .env dosyasını Railway prod değerleriyle onarır (sırları stdout'a yazmaz)."""
from __future__ import annotations

import pathlib
import re
import sys

from scripts.fetch_railway_env import fetch_service_variables

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _read_existing() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    out: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        out[key.strip()] = value.strip()
    return out


def main() -> int:
    try:
        railway = fetch_service_variables()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Railway env okunamadı: {exc}")
        return 1

    existing = _read_existing()
    service_key = railway.get("SUPABASE_SERVICE_KEY", "")
    cron_secret = railway.get("CRON_SECRET", "")
    supabase_url = railway.get("SUPABASE_URL") or existing.get("SUPABASE_URL", "")

    if not service_key or not supabase_url:
        print("❌ SUPABASE_URL veya SUPABASE_SERVICE_KEY Railway'de eksik")
        return 1

    gemini = existing.get("GEMINI_API_KEY", "")
    unsplash = existing.get("UNSPLASH_ACCESS_KEY", "")
    gemini_model = existing.get("GEMINI_MODEL", "gemini-2.5-flash")

    content = f"""# Niyetsen — yerel geliştirme (.env asla commit edilmez)
# Son onarım: scripts/fix_local_env.py (Railway prod ile senkron)

ENV=dev
AUTH_DISABLED=true

# Gemini
GEMINI_API_KEY={gemini}
GEMINI_MODEL={gemini_model}

# Görsel
UNSPLASH_ACCESS_KEY={unsplash}

# Supabase — service_role (publishable/anon DEĞİL)
SUPABASE_URL={supabase_url}
SUPABASE_SERVICE_KEY={service_key}
USE_SUPABASE_DB=true
# JWKS tabanlı imzalama; dev'de AUTH_DISABLED=true iken JWT secret gerekmez
SUPABASE_JWT_SECRET=

# Plan / rate limit
PLAN_BATCH_DAYS=7
MAX_TASKS_PER_DAY=5
CHAT_RATE_LIMIT_PER_MIN=10

# Cron (lokal test için Railway ile aynı)
CRON_SECRET={cron_secret}
"""
    ENV_PATH.write_text(content)
    print("✅ .env onarıldı")
    print("   - JWKS JSON bloğu kaldırıldı (dotenv parse hatası giderildi)")
    print("   - SUPABASE_SERVICE_KEY yalnızca service_role olarak yazıldı")
    print("   - CRON_SECRET Railway ile eşitlendi")
    return 0


if __name__ == "__main__":
    sys.exit(main())

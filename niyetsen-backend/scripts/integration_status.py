#!/usr/bin/env python3
"""Yerel .env ve prod health üzerinden entegrasyon özeti (sırları yazdırmaz)."""
from __future__ import annotations

import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

BACKEND_KEYS = [
    "ENV",
    "AUTH_DISABLED",
    "USE_SUPABASE_DB",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_MODEL_PLAN",
    "UNSPLASH_ACCESS_KEY",
    "REVENUECAT_WEBHOOK_SECRET",
    "CRON_SECRET",
    "CORS_ALLOWED_ORIGINS",
]

MOBILE_ENV = ROOT.parent / "mobile" / ".env"
MOBILE_KEYS = [
    "EXPO_PUBLIC_API_URL",
    "EXPO_PUBLIC_SUPABASE_URL",
    "EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    "EXPO_PUBLIC_REVENUECAT_API_KEY",
    "EXPO_PUBLIC_POSTHOG_KEY",
]


def load_env(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def status(key: str, value: str) -> str:
    if not value:
        return "❌ boş"
    if value.startswith("your-") or value in {"changeme", "xxx"}:
        return "⚠️ placeholder"
    return "✅ dolu"


def main() -> None:
    backend = load_env(ENV_PATH)
    mobile = load_env(MOBILE_ENV)

    print("=== Backend .env (yerel) ===")
    for key in BACKEND_KEYS:
        print(f"  {key}: {status(key, backend.get(key, ''))}")

    print("\n=== Mobile .env (yerel) ===")
    for key in MOBILE_KEYS:
        print(f"  {key}: {status(key, mobile.get(key, ''))}")

    api_url = mobile.get("EXPO_PUBLIC_API_URL") or "https://api-production-86f1.up.railway.app"
    health_url = api_url.rstrip("/") + "/health"
    print(f"\n=== Prod health ({health_url}) ===")
    try:
        with urllib.request.urlopen(health_url, timeout=15) as res:
            body = json.loads(res.read().decode())
        print(f"  HTTP {res.status}: {body}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ ulaşılamadı: {exc}")

    print("\n=== Entegrasyon özeti ===")
    print("  Supabase  → backend SUPABASE_* + mobile EXPO_PUBLIC_SUPABASE_*")
    print("  Railway   → prod API health + Railway Variables")
    print("  Gemini    → GEMINI_API_KEY + model flash(prod health doğruladı)")
    print("  Unsplash  → UNSPLASH_ACCESS_KEY (boşsa placeholder görseller)")
    print("  RevenueCat→ webhook Bearer + mobile EXPO_PUBLIC_REVENUECAT_API_KEY (EAS build)")


if __name__ == "__main__":
    main()

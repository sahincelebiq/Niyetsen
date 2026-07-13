#!/usr/bin/env python3
"""Prod Supabase şema + veri denetimi (Railway env'den service key alır)."""
from __future__ import annotations

import os
import sys

from scripts.fetch_railway_env import fetch_service_variables


def main() -> int:
    try:
        env = fetch_service_variables()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Railway env okunamadı: {exc}")
        return 1

    os.environ["SUPABASE_URL"] = env.get("SUPABASE_URL", "")
    os.environ["SUPABASE_SERVICE_KEY"] = env.get("SUPABASE_SERVICE_KEY", "")
    os.environ["USE_SUPABASE_DB"] = "true"

    if not os.environ["SUPABASE_URL"] or not os.environ["SUPABASE_SERVICE_KEY"]:
        print("❌ Railway API servisinde SUPABASE_URL / SUPABASE_SERVICE_KEY eksik.")
        return 1

    from scripts.audit_supabase_schema import main as audit_main

    return audit_main()


if __name__ == "__main__":
    sys.exit(main())

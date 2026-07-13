#!/usr/bin/env python3
"""Prod Supabase veri onarımı (DDL yok — güvenli)."""
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

    url = env.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("❌ SUPABASE_URL veya SUPABASE_SERVICE_KEY Railway'de eksik.")
        return 1

    from supabase import create_client

    db = create_client(url, key)

    bad_tasks = (
        db.table("tasks")
        .select("id")
        .is_("categories", "null")
        .limit(500)
        .execute()
        .data
    )
    empty = (
        db.table("tasks")
        .select("id,categories")
        .limit(500)
        .execute()
        .data
    )
    empty_ids = [
        row["id"]
        for row in empty
        if not row.get("categories")
    ]

    repaired = 0
    for task_id in {row["id"] for row in bad_tasks} | set(empty_ids):
        db.table("tasks").update({"categories": ["İrade"]}).eq("id", task_id).execute()
        repaired += 1

    users = db.table("users").select("id").execute().data
    streaks = {row["user_id"] for row in db.table("streaks").select("user_id").execute().data}
    backfilled = 0
    for row in users:
        if row["id"] not in streaks:
            db.table("streaks").insert({
                "user_id": row["id"],
                "current_len": 0,
                "best_len": 0,
                "silent_miss_streak": 0,
            }).execute()
            backfilled += 1

    print(f"✅ tasks categories onarımı: {repaired}")
    print(f"✅ streaks backfill: {backfilled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prod Supabase VERIFY_HEALTH.sql sorgularını çalıştırır."""
from __future__ import annotations

import sys

from scripts.fetch_railway_env import fetch_service_variables


def main() -> int:
    try:
        env = fetch_service_variables()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Railway env: {exc}")
        return 1

    url = env.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("❌ SUPABASE credentials eksik")
        return 1

    from supabase import create_client

    db = create_client(url, key)

    tables = [
        "users", "streaks", "points", "plans", "tasks", "chat_msgs", "intents",
        "proofs", "point_log", "push_tokens", "bonus_offers", "user_consents",
        "proof_requests",
    ]
    missing_tables = []
    for table in tables:
        try:
            db.table(table).select("*").limit(1).execute()
        except Exception:
            missing_tables.append(table)

    user_cols = (
        db.table("users")
        .select("active_plan_id,trial_started_at,subscription_expires_at,timezone,subscription_status")
        .limit(1)
        .execute()
    )
    plan_cols = db.table("plans").select("name,slot_no").limit(1).execute()

    users = db.table("users").select("id", count="exact").execute().count or 0
    streaks = db.table("streaks").select("user_id", count="exact").execute().count or 0
    plans = db.table("plans").select("id", count="exact").execute().count or 0

    all_users = db.table("users").select("id").execute().data
    all_streaks = {r["user_id"] for r in db.table("streaks").select("user_id").execute().data}
    users_without_streak = sum(1 for u in all_users if u["id"] not in all_streaks)

    tasks = db.table("tasks").select("id,categories").limit(1000).execute().data
    bad_categories = sum(
        1 for t in tasks if t.get("categories") is None or len(t.get("categories") or []) == 0
    )

    print("=== VERIFY_HEALTH ===")
    print(f"tables missing: {missing_tables or 'none'}")
    print(f"users columns ok: {bool(user_cols.data is not None)}")
    print(f"plans columns ok: {bool(plan_cols.data is not None)}")
    print(f"users={users} streaks={streaks} plans={plans}")
    print(f"users_without_streak={users_without_streak}")
    print(f"tasks_bad_categories(sample)={bad_categories}")

    if missing_tables or users_without_streak or bad_categories:
        return 1
    print("✅ VERIFY_HEALTH temiz")
    return 0


if __name__ == "__main__":
    sys.exit(main())

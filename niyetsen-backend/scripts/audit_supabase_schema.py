#!/usr/bin/env python3
"""Supabase şema denetimi — yalnızca okuma; sırları yazdırmaz."""
from __future__ import annotations

import sys

from app.config import settings

REQUIRED_USER_COLUMNS = (
    "id",
    "timezone",
    "excuse_count",
    "freeze_tokens",
    "freeze_last_grant",
    "active_plan_id",
    "trial_started_at",
    "subscription_expires_at",
    "subscription_status",
    "notif_hour",
)

REQUIRED_PLAN_COLUMNS = ("id", "user_id", "name", "slot_no", "duration_days", "start_date")
REQUIRED_TASK_COLUMNS = ("id", "plan_id", "day_no", "categories", "status", "date")


def main() -> int:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL veya SUPABASE_SERVICE_KEY boş.")
        return 1

    from supabase import create_client

    db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    errors: list[str] = []

    checks = [
        ("users", ",".join(REQUIRED_USER_COLUMNS)),
        ("plans", ",".join(REQUIRED_PLAN_COLUMNS)),
        ("tasks", ",".join(REQUIRED_TASK_COLUMNS)),
        ("streaks", "user_id,current_len,best_len,last_active_date,silent_miss_streak"),
        ("push_tokens", "user_id,token,enabled,last_task_reminder_date,last_bonus_offer_date"),
        ("chat_msgs", "user_id,plan_id,client_message_id,role,content"),
    ]

    for table, columns in checks:
        try:
            db.table(table).select(columns).limit(1).execute()
            print(f"✅ {table}: gerekli kolonlar erişilebilir")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{table}: {exc}")
            print(f"❌ {table}: {exc}")

    # Veri bütünlüğü: null categories veya bozuk tarih
    try:
        bad_tasks = (
            db.table("tasks")
            .select("id,plan_id,categories,date")
            .is_("categories", "null")
            .limit(5)
            .execute()
            .data
        )
        if bad_tasks:
            errors.append(f"tasks: {len(bad_tasks)} satırda categories=NULL")
            print(f"⚠️  tasks: categories=NULL olan örnekler: {[r['id'] for r in bad_tasks]}")
        else:
            print("✅ tasks: categories=NULL satır yok (örneklem)")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"tasks null check: {exc}")
        print(f"❌ tasks null check: {exc}")

    if errors:
        print(f"\n❌ {len(errors)} şema/veri sorunu bulundu.")
        return 1

    print("\n✅ Supabase şema denetimi temiz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

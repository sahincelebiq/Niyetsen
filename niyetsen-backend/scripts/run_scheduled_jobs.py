"""Railway cron entrypoint — yalnızca direct mod (Supabase doğrudan)."""
from __future__ import annotations

import json
import os
import sys
import traceback


def _log_env_diagnostic() -> None:
    checks = {
        "CRON_EXECUTION_MODE": "direct",
        "ENV": os.environ.get("ENV", "(yok)"),
        "USE_SUPABASE_DB": os.environ.get("USE_SUPABASE_DB", "(yok)"),
        "SUPABASE_URL": "set" if os.environ.get("SUPABASE_URL") else "MISSING",
        "SUPABASE_SERVICE_KEY": "set" if os.environ.get("SUPABASE_SERVICE_KEY") else "MISSING",
        "CRON_SKIP_PUSH": os.environ.get("CRON_SKIP_PUSH", "false"),
    }
    print("cron env: " + json.dumps(checks, ensure_ascii=False))


def _require_direct_env() -> None:
    missing: list[str] = []
    if os.environ.get("USE_SUPABASE_DB", "").strip().lower() != "true":
        missing.append("USE_SUPABASE_DB=true")
    if not os.environ.get("SUPABASE_URL", "").strip():
        missing.append("SUPABASE_URL")
    if not os.environ.get("SUPABASE_SERVICE_KEY", "").strip():
        missing.append("SUPABASE_SERVICE_KEY")
    if missing:
        raise RuntimeError(
            "Cron direct mod için eksik env: "
            + ", ".join(missing)
            + " — python -m scripts.sync_cron_railway_env çalıştır"
        )


def _print_result(label: str, payload: dict) -> None:
    print(f"{label}: {json.dumps(payload, ensure_ascii=False)[:800]}")


def run_jobs() -> tuple[list[str], list[str]]:
    from app.services import notification_service, task_lifecycle_service
    from app.storage.repository import repo

    hard_failures: list[str] = []
    soft_failures: list[str] = []
    skip_push = os.environ.get("CRON_SKIP_PUSH", "").strip().lower() in ("1", "true", "yes")

    try:
        close_result = task_lifecycle_service.close_due_users(repo)
        _print_result("close-day", close_result)
        if close_result.get("failed_users", 0) > 0:
            soft_failures.append(
                f"close-day: {close_result['failed_users']} kullanıcı hatalı"
            )
        penalized = [
            row for row in close_result.get("results", [])
            if row.get("penalized_tasks", 0) > 0
        ]
        if penalized and not skip_push:
            try:
                sent = notification_service.send_penalty_notifications(repo, penalized)
                print(f"penalty_notifications_sent: {sent}")
            except Exception as exc:
                soft_failures.append(f"penalty_notifications: {exc}")
                print(f"penalty_notifications uyarı: {exc}", file=sys.stderr)
    except Exception as exc:
        hard_failures.append(f"close-day: {exc}")
        traceback.print_exc()

    if skip_push:
        print("notifications: atlandı (CRON_SKIP_PUSH=true)")
    else:
        try:
            notif_result = notification_service.run_due_notifications(repo)
            _print_result("notifications", notif_result)
        except Exception as exc:
            soft_failures.append(f"notifications: {exc}")
            print(f"notifications uyarı: {exc}", file=sys.stderr)

    return hard_failures, soft_failures


def main() -> None:
    print("cron modu: direct")
    _log_env_diagnostic()

    try:
        _require_direct_env()
        hard_failures, soft_failures = run_jobs()
    except Exception as exc:
        print(f"cron beklenmeyen hata: {exc}", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1) from exc

    if soft_failures:
        print("uyarılar:\n" + "\n".join(soft_failures), file=sys.stderr)

    if hard_failures:
        print("hatalar:\n" + "\n".join(hard_failures), file=sys.stderr)
        raise SystemExit(1)

    print("cron tamamlandı (exit 0)")


if __name__ == "__main__":
    main()

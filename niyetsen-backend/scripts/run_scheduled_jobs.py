"""Railway cron entrypoint — direct mod, çökmez (her zaman exit 0)."""
from __future__ import annotations

import json
import os
import signal
import sys
import time
import traceback
from pathlib import Path

# Dockerfile CMD uvicorn olsa bile cron script app.* import edebilsin.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

# Yeni Supabase key adları → backend'in beklediği isim
if not os.environ.get("SUPABASE_SERVICE_KEY") and os.environ.get("SUPABASE_SECRET_KEY"):
    os.environ["SUPABASE_SERVICE_KEY"] = os.environ["SUPABASE_SECRET_KEY"]
if not os.environ.get("SUPABASE_URL") and os.environ.get("NEXT_PUBLIC_SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = os.environ["NEXT_PUBLIC_SUPABASE_URL"]


def _service_key_set() -> bool:
    return bool(
        os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
        or os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    )


def _log_env_diagnostic() -> None:
    checks = {
        "mod": "direct",
        "ENV": os.environ.get("ENV", "(yok)"),
        "USE_SUPABASE_DB": os.environ.get("USE_SUPABASE_DB", "(yok)"),
        "SUPABASE_URL": "set" if os.environ.get("SUPABASE_URL") else "MISSING",
        "SUPABASE_SERVICE_KEY": "set" if _service_key_set() else "MISSING",
        "CRON_SKIP_PUSH": os.environ.get("CRON_SKIP_PUSH", "false"),
        "SUPABASE_TIMEOUT_SEC": os.environ.get("SUPABASE_TIMEOUT_SEC", "120"),
    }
    print("cron env: " + json.dumps(checks, ensure_ascii=False))


def _missing_env() -> list[str]:
    missing: list[str] = []
    if os.environ.get("USE_SUPABASE_DB", "").strip().lower() != "true":
        missing.append("USE_SUPABASE_DB=true")
    if not os.environ.get("SUPABASE_URL", "").strip():
        missing.append("SUPABASE_URL")
    if not _service_key_set():
        missing.append("SUPABASE_SERVICE_KEY veya SUPABASE_SECRET_KEY")
    return missing


def _print_result(label: str, payload: dict) -> None:
    print(f"{label}: {json.dumps(payload, ensure_ascii=False)[:800]}")


def _run_with_retry(label: str, fn, *, retries: int = 2, backoff_sec: float = 3.0):
    """Supabase/httpx timeout'ta cron çökmesin — 2 deneme."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            err = str(exc).lower()
            retryable = any(
                token in err or token in type(exc).__name__.lower()
                for token in ("timeout", "timed out", "readtimeout", "connect")
            )
            if retryable and attempt < retries - 1:
                wait = backoff_sec * (attempt + 1)
                print(
                    f"{label}: geçici hata ({type(exc).__name__}), "
                    f"{wait:.0f}s sonra yeniden denenecek…"
                )
                time.sleep(wait)
                continue
            raise
    assert last_exc is not None
    raise last_exc


def run_jobs() -> list[str]:
    """Tüm adımlar hata verse bile liste döner; exception dışarı taşmaz."""
    warnings: list[str] = []
    skip_push = os.environ.get("CRON_SKIP_PUSH", "").strip().lower() in ("1", "true", "yes")

    try:
        from app.services import notification_service, task_lifecycle_service
        from app.storage.repository import repo
    except Exception as exc:
        warnings.append(f"import: {exc}")
        traceback.print_exc()
        return warnings

    # Railway cron 5 dk'da bir tetikler; tur asla pencereyi taşmasın.
    budget_sec = float(os.environ.get("CRON_TIME_BUDGET_SEC", "240"))
    deadline_ts = time.monotonic() + budget_sec

    try:
        close_result = _run_with_retry(
            "close-day",
            lambda: task_lifecycle_service.close_due_users(
                repo, deadline_ts=deadline_ts
            ),
        )
        _print_result("close-day", close_result)
        failed = close_result.get("failed_users", 0)
        if failed:
            warnings.append(f"close-day: {failed} kullanıcı işlenemedi")
            for row in (close_result.get("user_errors") or [])[:3]:
                warnings.append(f"  user {row.get('user_id')}: {row.get('error', '')[:120]}")

        if not skip_push:
            penalized = [
                row for row in close_result.get("results", [])
                if row.get("penalized_tasks", 0) > 0
            ]
            if penalized:
                try:
                    sent = _run_with_retry(
                        "penalty_notifications",
                        lambda: notification_service.send_penalty_notifications(
                            repo, penalized
                        ),
                    )
                    print(f"penalty_notifications_sent: {sent}")
                except Exception as exc:
                    warnings.append(f"penalty_notifications: {exc}")
                    traceback.print_exc()
    except Exception as exc:
        warnings.append(f"close-day: {exc}")
        traceback.print_exc()

    if skip_push:
        print("notifications: atlandı (CRON_SKIP_PUSH=true)")
    else:
        try:
            notif_result = _run_with_retry(
                "notifications",
                lambda: notification_service.run_due_notifications(repo),
            )
            _print_result("notifications", notif_result)
        except Exception as exc:
            warnings.append(f"notifications: {exc}")
            traceback.print_exc()

    return warnings


def _graceful_exit(signum: int, _frame) -> None:
    """Railway redeploy/limit SIGTERM gönderirse süreç 143 ile ölmesin.

    Nonzero exit Railway'de 'Deploy Crashed' maili üretir; işler idempotent
    olduğundan yarım kalan tur bir sonraki 5 dk tetiklemesinde tamamlanır.
    """
    print(f"cron: sinyal alındı ({signum}) — temiz çıkış (exit 0)", file=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _graceful_exit)
    signal.signal(signal.SIGINT, _graceful_exit)
    print("cron modu: direct")
    _log_env_diagnostic()

    missing = _missing_env()
    if missing:
        print(
            "cron env eksik — iş atlandı (mail spam önleme, exit 0): "
            + ", ".join(missing),
            file=sys.stderr,
        )
        print("çözüm: python -m scripts.sync_cron_railway_env")
        return

    try:
        warnings = run_jobs()
    except Exception as exc:
        warnings = [f"cron beklenmeyen hata: {exc}"]
        traceback.print_exc()

    if warnings:
        print("uyarılar:\n" + "\n".join(warnings), file=sys.stderr)

    print("cron tamamlandı (exit 0)")


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # noqa: BLE001 — cron ASLA nonzero exit vermez
        traceback.print_exc()
        print("cron: beklenmeyen üst seviye hata — yine de exit 0", file=sys.stderr)
    sys.exit(0)

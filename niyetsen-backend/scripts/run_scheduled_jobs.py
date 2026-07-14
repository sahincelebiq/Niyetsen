"""Railway cron entrypoint. Runs scheduled jobs and exits."""
from __future__ import annotations

import json
import os
import sys
import traceback

# Cron servisi varsayılan olarak direct modda çalışır (Supabase doğrudan).
# HTTP modu yalnızca yerel geliştirme için: CRON_EXECUTION_MODE=http
DEFAULT_MODE = "direct"


def _execution_mode() -> str:
    configured = os.environ.get("CRON_EXECUTION_MODE", DEFAULT_MODE).strip().lower()
    if configured in {"direct", "http"}:
        return configured
    return DEFAULT_MODE


def _log_env_diagnostic() -> None:
    checks = {
        "CRON_EXECUTION_MODE": os.environ.get("CRON_EXECUTION_MODE", f"(varsayılan {DEFAULT_MODE})"),
        "ENV": os.environ.get("ENV", "(yok)"),
        "USE_SUPABASE_DB": os.environ.get("USE_SUPABASE_DB", "(yok)"),
        "SUPABASE_URL": "set" if os.environ.get("SUPABASE_URL") else "MISSING",
        "SUPABASE_SERVICE_KEY": "set" if os.environ.get("SUPABASE_SERVICE_KEY") else "MISSING",
        "API_BASE_URL": os.environ.get("API_BASE_URL", "(yok)"),
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
            "Direct cron için eksik Railway env: "
            + ", ".join(missing)
            + ". Çalıştır: python -m scripts.sync_cron_railway_env"
        )


def _print_result(label: str, payload: dict) -> None:
    print(f"{label}: {json.dumps(payload, ensure_ascii=False)[:800]}")


def run_jobs_direct() -> tuple[list[str], list[str]]:
    """Supabase'e doğrudan bağlanır — API HTTP hop yok."""
    from app.services import notification_service, task_lifecycle_service
    from app.storage.repository import repo

    hard_failures: list[str] = []
    soft_failures: list[str] = []
    skip_push = os.environ.get("CRON_SKIP_PUSH", "").strip().lower() in ("1", "true", "yes")

    try:
        close_result = task_lifecycle_service.close_due_users(repo)
        _print_result("close-day", close_result)
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


def run_jobs_http() -> tuple[list[str], list[str]]:
    """Yerel geliştirme yedek yolu — prod cron bu modu kullanmamalı."""
    import time

    import httpx
    from httpx import ConnectError, ConnectTimeout, ReadTimeout, Timeout, WriteTimeout

    connect_timeout = float(os.environ.get("CRON_CONNECT_TIMEOUT", "15"))
    read_timeout = float(os.environ.get("CRON_READ_TIMEOUT", "300"))
    max_retries = int(os.environ.get("CRON_MAX_RETRIES", "3"))
    retry_backoff = (5, 15, 30)

    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("HTTP mod: API_BASE_URL ve CRON_SECRET zorunlu.")

    client_timeout = Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=30.0,
        pool=connect_timeout,
    )
    headers = {"X-Cron-Secret": secret}
    hard_failures: list[str] = []
    soft_failures: list[str] = []

    def post_with_retry(client: httpx.Client, url: str) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return client.post(url, headers=headers)
            except (ReadTimeout, ConnectTimeout, WriteTimeout, ConnectError) as exc:
                last_exc = exc
                if attempt >= max_retries - 1:
                    break
                wait = retry_backoff[min(attempt, len(retry_backoff) - 1)]
                print(
                    f"{url}: geçici ağ hatası ({type(exc).__name__}), "
                    f"deneme {attempt + 1}/{max_retries}, {wait}s bekleniyor…"
                )
                time.sleep(wait)
        assert last_exc is not None
        raise last_exc

    with httpx.Client(timeout=client_timeout) as client:
        jobs: list[tuple[str, str, bool]] = [
            ("/cron/close-day", "close-day", True),
            ("/cron/notifications", "notifications", False),
        ]
        for endpoint, label, is_critical in jobs:
            url = f"{base_url}{endpoint}"
            try:
                response = post_with_retry(client, url)
            except (ReadTimeout, ConnectTimeout, WriteTimeout) as exc:
                message = (
                    f"{label}: zaman aşımı ({type(exc).__name__}) "
                    f"— read={read_timeout}s, {max_retries} deneme tükendi"
                )
                (hard_failures if is_critical else soft_failures).append(message)
                continue
            except ConnectError as exc:
                message = f"{label}: bağlantı hatası — {exc}"
                (hard_failures if is_critical else soft_failures).append(message)
                continue

            if response.status_code == 404 and endpoint == "/cron/notifications":
                print(f"{endpoint}: 404 (atlandı)")
                continue
            if response.status_code == 401:
                hard_failures.append(f"{label}: 401 CRON_SECRET eşleşmiyor")
                continue
            if response.is_error:
                message = f"{label}: {response.status_code} {response.text[:200]}"
                (hard_failures if is_critical else soft_failures).append(message)
            else:
                print(f"{endpoint}: {response.status_code} {response.text[:500]}")

    return hard_failures, soft_failures


def main() -> None:
    mode = _execution_mode()
    print(f"cron modu: {mode}")
    _log_env_diagnostic()

    try:
        if mode == "direct":
            _require_direct_env()
            hard_failures, soft_failures = run_jobs_direct()
        else:
            print("uyarı: HTTP modu — yalnızca yerel test için önerilir", file=sys.stderr)
            hard_failures, soft_failures = run_jobs_http()
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

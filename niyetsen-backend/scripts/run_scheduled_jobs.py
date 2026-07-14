"""Railway cron entrypoint. Runs scheduled jobs and exits."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

import httpx
from httpx import ConnectError, ConnectTimeout, ReadTimeout, Timeout, WriteTimeout

DEFAULT_CONNECT_TIMEOUT = float(os.environ.get("CRON_CONNECT_TIMEOUT", "15"))
DEFAULT_READ_TIMEOUT = float(os.environ.get("CRON_READ_TIMEOUT", "300"))
MAX_RETRIES = int(os.environ.get("CRON_MAX_RETRIES", "3"))
RETRY_BACKOFF_SEC = (5, 15, 30)


def _execution_mode() -> str:
    configured = os.environ.get("CRON_EXECUTION_MODE", "").strip().lower()
    if configured in {"direct", "http"}:
        return configured
    if os.environ.get("USE_SUPABASE_DB", "").strip().lower() == "true":
        if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"):
            return "direct"
    return "http"


def _client_timeout() -> Timeout:
    return Timeout(
        connect=DEFAULT_CONNECT_TIMEOUT,
        read=DEFAULT_READ_TIMEOUT,
        write=30.0,
        pool=DEFAULT_CONNECT_TIMEOUT,
    )


def _post_with_retry(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.post(url, headers=headers)
        except (ReadTimeout, ConnectTimeout, WriteTimeout, ConnectError) as exc:
            last_exc = exc
            if attempt >= MAX_RETRIES - 1:
                break
            wait = RETRY_BACKOFF_SEC[min(attempt, len(RETRY_BACKOFF_SEC) - 1)]
            print(
                f"{url}: geçici ağ hatası ({type(exc).__name__}), "
                f"deneme {attempt + 1}/{MAX_RETRIES}, {wait}s bekleniyor…"
            )
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def _print_result(label: str, payload: dict) -> None:
    print(f"{label}: {json.dumps(payload, ensure_ascii=False)[:800]}")


def run_jobs_direct() -> tuple[list[str], list[str]]:
    """Supabase'e doğrudan bağlanır — HTTP hop yok, ReadTimeout riski yok."""
    from app.services import notification_service, task_lifecycle_service
    from app.storage.repository import repo

    hard_failures: list[str] = []
    soft_failures: list[str] = []

    try:
        close_result = task_lifecycle_service.close_due_users(repo)
        _print_result("close-day", close_result)
        penalized = [
            row for row in close_result.get("results", [])
            if row.get("penalized_tasks", 0) > 0
        ]
        if penalized:
            try:
                sent = notification_service.send_penalty_notifications(repo, penalized)
                print(f"penalty_notifications_sent: {sent}")
            except Exception as exc:
                soft_failures.append(f"penalty_notifications: {exc}")
                print(f"penalty_notifications uyarı: {exc}", file=sys.stderr)
    except Exception as exc:
        hard_failures.append(f"close-day: {exc}")
        traceback.print_exc()

    try:
        notif_result = notification_service.run_due_notifications(repo)
        _print_result("notifications", notif_result)
    except Exception as exc:
        soft_failures.append(f"notifications: {exc}")
        print(f"notifications uyarı: {exc}", file=sys.stderr)

    return hard_failures, soft_failures


def run_jobs_http() -> tuple[list[str], list[str]]:
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("API_BASE_URL ve CRON_SECRET cron servisinde zorunlu.")

    headers = {"X-Cron-Secret": secret}
    hard_failures: list[str] = []
    soft_failures: list[str] = []

    with httpx.Client(timeout=_client_timeout()) as client:
        health = f"{base_url}/health"
        try:
            ping = client.get(health, timeout=Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0))
            print(f"/health: {ping.status_code}")
        except Exception as exc:
            print(f"/health uyarı: {exc}")

        jobs: list[tuple[str, str, bool]] = [
            ("/cron/close-day", "close-day", True),
            ("/cron/notifications", "notifications", False),
        ]
        for endpoint, label, is_critical in jobs:
            url = f"{base_url}{endpoint}"
            try:
                response = _post_with_retry(client, url, headers)
            except (ReadTimeout, ConnectTimeout, WriteTimeout) as exc:
                message = (
                    f"{label}: zaman aşımı ({type(exc).__name__}) "
                    f"— read={DEFAULT_READ_TIMEOUT}s, {MAX_RETRIES} deneme tükendi"
                )
                (hard_failures if is_critical else soft_failures).append(message)
                continue
            except ConnectError as exc:
                message = f"{label}: bağlantı hatası — {exc}"
                (hard_failures if is_critical else soft_failures).append(message)
                continue

            if response.status_code == 404 and endpoint == "/cron/notifications":
                print(f"{endpoint}: 404 (henüz deploy edilmemiş, atlandı)")
                continue
            if response.status_code == 401:
                hard_failures.append(
                    f"{label}: 401 CRON_SECRET eşleşmiyor "
                    f"(API ve cron servisinde aynı değer olmalı)"
                )
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

    try:
        if mode == "direct":
            if os.environ.get("USE_SUPABASE_DB", "").strip().lower() != "true":
                raise RuntimeError(
                    "CRON_EXECUTION_MODE=direct için USE_SUPABASE_DB=true gerekli."
                )
            hard_failures, soft_failures = run_jobs_direct()
        else:
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

"""Railway cron entrypoint. Calls idempotent API jobs and exits."""
from __future__ import annotations

import os
import sys
import time

import httpx

RETRYABLE_STATUS = {500, 502, 503, 504}
MAX_ATTEMPTS = 3
RETRY_DELAY_SEC = 2.0


def _post_with_retry(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
) -> httpx.Response:
    last_response: httpx.Response | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.post(url, headers=headers)
        except httpx.RequestError as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            print(
                f"İstek hatası (deneme {attempt}/{MAX_ATTEMPTS}): {exc}",
                file=sys.stderr,
            )
            time.sleep(RETRY_DELAY_SEC * attempt)
            continue
        if response.status_code not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS:
            return response
        print(
            f"Geçici hata {response.status_code} (deneme {attempt}/{MAX_ATTEMPTS}), "
            f"tekrar deneniyor…",
            file=sys.stderr,
        )
        time.sleep(RETRY_DELAY_SEC * attempt)
        last_response = response
    return last_response  # type: ignore[return-value]


def main() -> None:
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("API_BASE_URL ve CRON_SECRET cron servisinde zorunlu.")

    endpoints = ["/cron/close-day", "/cron/notifications"]
    headers = {"X-Cron-Secret": secret}
    failures: list[str] = []
    warnings: list[str] = []
    with httpx.Client(timeout=90) as client:
        for endpoint in endpoints:
            response = _post_with_retry(client, f"{base_url}{endpoint}", headers)
            if response.status_code == 404 and endpoint == "/cron/notifications":
                # FAZ 4 endpoint'i deploy edilene kadar close-day çalışmaya devam eder.
                continue
            if response.is_error:
                failures.append(
                    f"{endpoint}: {response.status_code} {response.text[:500]}"
                )
                continue
            body_preview = response.text[:500]
            print(f"{endpoint}: {response.status_code} {body_preview}")
            if endpoint == "/cron/close-day":
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                user_errors = payload.get("user_errors") or []
                if user_errors:
                    warnings.append(
                        f"{endpoint}: {len(user_errors)} kullanıcı işlenemedi"
                    )
                    for row in user_errors[:5]:
                        warnings.append(f"  - {row.get('user_id')}: {row.get('error')}")

    if warnings:
        print("\n".join(warnings), file=sys.stderr)

    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

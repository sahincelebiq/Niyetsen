"""Railway cron entrypoint. Calls idempotent API jobs and exits."""
from __future__ import annotations

import os
import sys
import time

import httpx
from httpx import ConnectError, ConnectTimeout, ReadTimeout, Timeout, WriteTimeout

DEFAULT_CONNECT_TIMEOUT = float(os.environ.get("CRON_CONNECT_TIMEOUT", "15"))
DEFAULT_READ_TIMEOUT = float(os.environ.get("CRON_READ_TIMEOUT", "300"))
MAX_RETRIES = int(os.environ.get("CRON_MAX_RETRIES", "3"))
RETRY_BACKOFF_SEC = (5, 15, 30)


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


def main() -> None:
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("API_BASE_URL ve CRON_SECRET cron servisinde zorunlu.")

    endpoints = ["/cron/close-day", "/cron/notifications"]
    headers = {"X-Cron-Secret": secret}
    failures: list[str] = []
    try:
        with httpx.Client(timeout=_client_timeout()) as client:
            for endpoint in endpoints:
                url = f"{base_url}{endpoint}"
                try:
                    response = _post_with_retry(client, url, headers)
                except (ReadTimeout, ConnectTimeout, WriteTimeout) as exc:
                    failures.append(
                        f"{endpoint}: zaman aşımı ({type(exc).__name__}) "
                        f"— read={DEFAULT_READ_TIMEOUT}s, {MAX_RETRIES} deneme tükendi"
                    )
                    continue
                except ConnectError as exc:
                    failures.append(f"{endpoint}: bağlantı hatası — {exc}")
                    continue

                if response.status_code == 404 and endpoint == "/cron/notifications":
                    # FAZ 4 endpoint'i deploy edilene kadar close-day çalışmaya devam eder.
                    print(f"{endpoint}: 404 (henüz deploy edilmemiş, atlandı)")
                    continue
                if response.status_code == 401:
                    failures.append(
                        f"{endpoint}: 401 CRON_SECRET eşleşmiyor veya eksik "
                        f"(API ve cron servisinde aynı değer olmalı)"
                    )
                    continue
                if response.is_error:
                    failures.append(
                        f"{endpoint}: {response.status_code} {response.text[:200]}"
                    )
                else:
                    print(f"{endpoint}: {response.status_code} {response.text[:500]}")
    except Exception as exc:
        print(f"cron beklenmeyen hata: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

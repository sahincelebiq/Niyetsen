"""Railway cron entrypoint. Calls idempotent API jobs and exits."""
from __future__ import annotations

import os
import sys

import httpx


def main() -> None:
    base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
    secret = os.environ.get("CRON_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("API_BASE_URL ve CRON_SECRET cron servisinde zorunlu.")

    endpoints = ["/cron/close-day", "/cron/notifications"]
    headers = {"X-Cron-Secret": secret}
    failures: list[str] = []
    with httpx.Client(timeout=60) as client:
        for endpoint in endpoints:
            response = client.post(f"{base_url}{endpoint}", headers=headers)
            if response.status_code == 404 and endpoint == "/cron/notifications":
                # FAZ 4 endpoint'i deploy edilene kadar close-day çalışmaya devam eder.
                continue
            if response.is_error:
                failures.append(f"{endpoint}: {response.status_code} {response.text[:200]}")
            else:
                print(f"{endpoint}: {response.status_code} {response.text[:500]}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

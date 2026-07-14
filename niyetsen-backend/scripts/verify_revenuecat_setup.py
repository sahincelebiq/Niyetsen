#!/usr/bin/env python3
"""KAPI 5 — RevenueCat + paywall altyapısı doğrulama (Railway prod)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import httpx

DEFAULT_API = "https://api-production-86f1.up.railway.app"


def main() -> int:
    parser = argparse.ArgumentParser(description="RevenueCat webhook ve API kontrolü")
    parser.add_argument("--api-base", default=os.environ.get("API_BASE_URL", DEFAULT_API))
    parser.add_argument("--webhook-secret", default=os.environ.get("REVENUECAT_WEBHOOK_SECRET", ""))
    parser.add_argument("--test-user", default="sandbox-verify-user")
    args = parser.parse_args()
    base = args.api_base.rstrip("/")
    ok = True

    health = httpx.get(f"{base}/health", timeout=15)
    print(f"health: {health.status_code}")
    ok &= health.status_code == 200

    no_auth = httpx.post(f"{base}/webhooks/revenuecat", json={"event": {}}, timeout=15)
    print(f"webhook without auth: {no_auth.status_code} (expect 401)")
    ok &= no_auth.status_code == 401

    if args.webhook_secret:
        expires_ms = int(datetime(2099, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        payload = {
            "event": {
                "type": "INITIAL_PURCHASE",
                "app_user_id": args.test_user,
                "expiration_at_ms": expires_ms,
                "id": "verify-script",
            }
        }
        res = httpx.post(
            f"{base}/webhooks/revenuecat",
            headers={"Authorization": f"Bearer {args.webhook_secret}"},
            json=payload,
            timeout=15,
        )
        print(f"webhook sandbox activate: {res.status_code}")
        try:
            print(json.dumps(res.json(), indent=2, ensure_ascii=False))
        except Exception:
            print(res.text[:300])
        ok &= res.status_code == 200
    else:
        print("REVENUECAT_WEBHOOK_SECRET yok — webhook testi atlandı.")

    rc_key = os.environ.get("REVENUECAT_API_KEY", "").strip()
    if rc_key:
        rc = httpx.get(
            f"https://api.revenuecat.com/v1/subscribers/{args.test_user}",
            headers={"Authorization": f"Bearer {rc_key}"},
            timeout=15,
        )
        print(f"revenuecat REST: {rc.status_code}")
        ok &= rc.status_code in {200, 404}
    else:
        print("REVENUECAT_API_KEY yok — REST senkron testi atlandı.")

    if not ok:
        print("Bazı kontroller başarısız.")
        return 1
    print("KAPI 5 altyapı kontrolleri tamam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

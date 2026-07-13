#!/usr/bin/env python3
"""Railway GraphQL: prod env + redeploy (CLI oturumu çalışmazsa yedek)."""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
CONFIG = pathlib.Path.home() / ".railway" / "config.json"
ROOT = pathlib.Path(__file__).resolve().parents[1]
SECRET_FILE = ROOT / ".railway-revenuecat-secret"

PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
SERVICE_ID = "4e9d589e-2bbf-4b93-a627-09697929a1ce"


def token() -> str:
    data = json.loads(CONFIG.read_text())
    return data["user"]["accessToken"]


def gql(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        payload = json.loads(res.read().decode())
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def main() -> int:
    secret = SECRET_FILE.read_text().strip()
    vars_to_set = {
        "ENV": "prod",
        "AUTH_DISABLED": "false",
        "USE_SUPABASE_DB": "true",
        "REVENUECAT_WEBHOOK_SECRET": secret,
    }

    me = gql("query { me { email } }")
    print(f"✓ Railway: {me['me']['email']}")

    for name, value in vars_to_set.items():
        gql(
            """
            mutation ($input: VariableUpsertInput!) {
              variableUpsert(input: $input)
            }
            """,
            {
                "input": {
                    "projectId": PROJECT_ID,
                    "environmentId": ENVIRONMENT_ID,
                    "serviceId": SERVICE_ID,
                    "name": name,
                    "value": value,
                }
            },
        )
        print(f"✓ variable {name}")

    gql(
        """
        mutation ($serviceId: String!, $environmentId: String!) {
          serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
        }
        """,
        {"serviceId": SERVICE_ID, "environmentId": ENVIRONMENT_ID},
    )
    print("✓ redeploy başlatıldı")
    print(f"✓ REVENUECAT webhook Bearer: Bearer {secret}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

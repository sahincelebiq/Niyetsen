#!/usr/bin/env python3
"""Railway api + cron servislerini yeniden deploy eder (Project-Access-Token)."""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
TOKEN_FILE = pathlib.Path(__file__).resolve().parents[1] / ".railway-project-token"


def _token() -> str:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise RuntimeError("Railway project token bulunamadı.")


def _gql(query: str, variables: dict | None = None) -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Project-Access-Token": _token(),
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        payload = json.loads(res.read().decode())
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def _service_ids() -> dict[str, str]:
    data = _gql(
        "query($id:String!){project(id:$id){services{edges{node{id name}}}}}",
        {"id": PROJECT_ID},
    )
    return {
        edge["node"]["name"]: edge["node"]["id"]
        for edge in data["project"]["services"]["edges"]
    }


def _redeploy(service_id: str) -> None:
    _gql(
        """
        mutation ($serviceId: String!, $environmentId: String!) {
          serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
        }
        """,
        {"serviceId": service_id, "environmentId": ENVIRONMENT_ID},
    )


def main() -> int:
    services = _service_ids()
    for name in ("api", "cron"):
        service_id = services.get(name)
        if not service_id:
            print(f"❌ {name} servisi bulunamadı")
            return 1
        _redeploy(service_id)
        print(f"✓ {name} redeploy başlatıldı ({service_id})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

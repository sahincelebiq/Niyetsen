#!/usr/bin/env python3
"""Railway cron servisinin direct veya HTTP yapılandırmasını doğrular."""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
API_SERVICE_ID = "4e9d589e-2bbf-4b93-a627-09697929a1ce"
TOKEN_FILE = pathlib.Path(__file__).resolve().parents[1] / ".railway-project-token"


def _token() -> str:
    if os.environ.get("RAILWAY_PROJECT_TOKEN"):
        return os.environ["RAILWAY_PROJECT_TOKEN"]
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise RuntimeError("RAILWAY_PROJECT_TOKEN yok.")


def _graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
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


def _service_variables(service_id: str) -> dict[str, str]:
    data = _graphql(
        "query($projectId:String!,$environmentId:String!,$serviceId:String!){"
        "variables(projectId:$projectId,environmentId:$environmentId,serviceId:$serviceId)}",
        {
            "projectId": PROJECT_ID,
            "environmentId": ENVIRONMENT_ID,
            "serviceId": service_id,
        },
    )
    return data["variables"]


def _resolve_cron_service_id() -> str:
    data = _graphql(
        "query($id:String!){project(id:$id){services{edges{node{id name}}}}}",
        {"id": PROJECT_ID},
    )
    for edge in data["project"]["services"]["edges"]:
        if edge["node"]["name"] == "cron":
            return edge["node"]["id"]
    raise RuntimeError("cron servisi bulunamadı")


def main() -> int:
    cron_id = _resolve_cron_service_id()
    api_vars = _service_variables(API_SERVICE_ID)
    cron_vars = _service_variables(cron_id)

    api_secret = api_vars.get("CRON_SECRET", "")
    cron_secret = cron_vars.get("CRON_SECRET", "")
    mode = cron_vars.get("CRON_EXECUTION_MODE", "").strip().lower()

    issues: list[str] = []
    if not api_secret:
        issues.append("API servisinde CRON_SECRET eksik")
    if not cron_secret:
        issues.append("Cron servisinde CRON_SECRET eksik")
    if api_secret and cron_secret and api_secret != cron_secret:
        issues.append("CRON_SECRET API ve cron servisinde farklı")

    if mode == "direct" or (
        cron_vars.get("USE_SUPABASE_DB", "").lower() == "true"
        and cron_vars.get("SUPABASE_URL")
        and cron_vars.get("SUPABASE_SERVICE_KEY")
    ):
        if cron_vars.get("USE_SUPABASE_DB", "").lower() != "true":
            issues.append("Direct mod için cron USE_SUPABASE_DB=true olmalı")
        if not cron_vars.get("SUPABASE_URL"):
            issues.append("Direct mod için cron SUPABASE_URL eksik")
        if not cron_vars.get("SUPABASE_SERVICE_KEY"):
            issues.append("Direct mod için cron SUPABASE_SERVICE_KEY eksik")
        mode_label = "direct"
    else:
        api_base = cron_vars.get("API_BASE_URL", "").rstrip("/")
        if not api_base:
            issues.append("HTTP mod için cron API_BASE_URL eksik")
        elif not api_base.startswith("https://"):
            issues.append("API_BASE_URL https ile başlamalı")
        mode_label = "http"

    if issues:
        print("❌ Cron yapılandırma sorunları:")
        for item in issues:
            print(f"  - {item}")
        return 1

    print("✅ Cron yapılandırması tutarlı")
    print(f"  mod={mode_label}")
    if mode_label == "direct":
        print(f"  SUPABASE_URL={cron_vars.get('SUPABASE_URL', '')[:40]}…")
    else:
        print(f"  API_BASE_URL={cron_vars.get('API_BASE_URL', '')}")
    print(f"  CRON_SECRET uzunluğu={len(cron_secret)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

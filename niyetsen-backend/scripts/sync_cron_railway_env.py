#!/usr/bin/env python3
"""API servisindeki Supabase env'lerini Railway cron servisine kopyalar (direct mod)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / ".railway-project-token"
BACKEND_ENV = ROOT / ".env"

COPY_KEYS = (
    "ENV",
    "USE_SUPABASE_DB",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "API_BASE_URL",
    "CRON_SECRET",
)


def _token() -> str:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    raise RuntimeError("Railway project token bulunamadı (.railway-project-token).")


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
    with urllib.request.urlopen(req, timeout=120) as res:
        payload = json.loads(res.read().decode())
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def _service_id(name: str) -> str:
    data = _gql(
        "query($id:String!){project(id:$id){services{edges{node{id name}}}}}",
        {"id": PROJECT_ID},
    )
    for edge in data["project"]["services"]["edges"]:
        if edge["node"]["name"] == name:
            return edge["node"]["id"]
    raise RuntimeError(f"Railway servisi bulunamadı: {name}")


def _parse_env(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        out[key.strip()] = value.strip()
    return out


def _railway_upsert(service_name: str, variables: dict[str, str]) -> None:
    service_id = _service_id(service_name)
    _gql(
        """
        mutation ($input: VariableCollectionUpsertInput!) {
          variableCollectionUpsert(input: $input)
        }
        """,
        {
            "input": {
                "projectId": PROJECT_ID,
                "environmentId": ENVIRONMENT_ID,
                "serviceId": service_id,
                "variables": variables,
                "skipDeploys": True,
            }
        },
    )


def main() -> int:
    local = _parse_env(BACKEND_ENV)
    missing = [key for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "CRON_SECRET") if not local.get(key)]
    if missing:
        print(f"❌ niyetsen-backend/.env eksik: {', '.join(missing)}")
        return 1

    cron_vars = {key: local[key] for key in COPY_KEYS if local.get(key)}
    cron_vars["ENV"] = local.get("ENV", "prod")
    cron_vars["USE_SUPABASE_DB"] = local.get("USE_SUPABASE_DB", "true")
    cron_vars["CRON_EXECUTION_MODE"] = "direct"
    cron_vars.setdefault(
        "API_BASE_URL",
        "https://api-production-86f1.up.railway.app",
    )

    print("Railway cron servisine direct-mod env yazılıyor…")
    _railway_upsert("cron", cron_vars)
    print("✓ cron: CRON_EXECUTION_MODE=direct + Supabase env senkronlandı")

    subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

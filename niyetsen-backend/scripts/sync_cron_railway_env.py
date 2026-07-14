#!/usr/bin/env python3
"""Railway API servisindeki env'leri cron servisine kopyalar (direct mod zorunlu)."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
API_SERVICE_ID = "4e9d589e-2bbf-4b93-a627-09697929a1ce"
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


def _service_variables(service_id: str) -> dict[str, str]:
    data = _gql(
        "query($projectId:String!,$environmentId:String!,$serviceId:String!){"
        "variables(projectId:$projectId,environmentId:$environmentId,serviceId:$serviceId)}",
        {
            "projectId": PROJECT_ID,
            "environmentId": ENVIRONMENT_ID,
            "serviceId": service_id,
        },
    )
    raw = data.get("variables")
    if isinstance(raw, dict):
        return raw
    return {}


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
                "skipDeploys": False,
            }
        },
    )


def main() -> int:
    api_vars = _service_variables(API_SERVICE_ID)
    local = _parse_env(BACKEND_ENV)

    source = {**local, **{k: v for k, v in api_vars.items() if v}}
    missing = [
        key for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "CRON_SECRET")
        if not source.get(key)
    ]
    if missing:
        print(f"❌ Kaynak env eksik (API Railway veya .env): {', '.join(missing)}")
        return 1

    cron_vars = {key: source[key] for key in COPY_KEYS if source.get(key)}
    cron_vars["ENV"] = source.get("ENV", "prod")
    cron_vars["USE_SUPABASE_DB"] = source.get("USE_SUPABASE_DB", "true")
    cron_vars["CRON_EXECUTION_MODE"] = "direct"
    cron_vars["CRON_SKIP_PUSH"] = "true"
    cron_vars["SUPABASE_TIMEOUT_SEC"] = source.get("SUPABASE_TIMEOUT_SEC", "120")
    cron_vars.setdefault(
        "API_BASE_URL",
        "https://api-production-86f1.up.railway.app",
    )

    print("Railway cron ← api env senkronu (direct mod)…")
    _railway_upsert("cron", cron_vars)
    print("✓ cron servisi güncellendi ve redeploy tetiklendi")
    print(f"  USE_SUPABASE_DB={cron_vars.get('USE_SUPABASE_DB')}")
    print(f"  SUPABASE_URL={'set' if cron_vars.get('SUPABASE_URL') else 'MISSING'}")
    print(f"  CRON_EXECUTION_MODE=direct")

    subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

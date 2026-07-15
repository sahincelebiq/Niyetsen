#!/usr/bin/env python3
"""Railway api + cron env senkronu (Supabase direct mod, çökmez cron)."""
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

SERVICE_NAMES = ("api", "cron")


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
    return raw if isinstance(raw, dict) else {}


def _parse_env(path: pathlib.Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        out[key.strip()] = value.strip().strip('"')
    return out


def _normalize(source: dict[str, str]) -> dict[str, str]:
    out = dict(source)
    if not out.get("SUPABASE_URL"):
        out["SUPABASE_URL"] = out.get("NEXT_PUBLIC_SUPABASE_URL", "")
    if not out.get("SUPABASE_SERVICE_KEY"):
        out["SUPABASE_SERVICE_KEY"] = out.get("SUPABASE_SECRET_KEY", "")
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


def _build_vars(source: dict[str, str], *, for_cron: bool) -> dict[str, str]:
    base = {
        "ENV": source.get("ENV", "prod"),
        "USE_SUPABASE_DB": source.get("USE_SUPABASE_DB", "true"),
        "SUPABASE_URL": source.get("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_KEY": source.get("SUPABASE_SERVICE_KEY", ""),
        "SUPABASE_TIMEOUT_SEC": source.get("SUPABASE_TIMEOUT_SEC", "120"),
        "CRON_SECRET": source.get("CRON_SECRET", ""),
    }
    if for_cron:
        base.update({
            "CRON_EXECUTION_MODE": "direct",
            "CRON_SKIP_PUSH": source.get("CRON_SKIP_PUSH", "true"),
            "API_BASE_URL": source.get(
                "API_BASE_URL",
                "https://api-production-86f1.up.railway.app",
            ),
        })
    return {k: v for k, v in base.items() if v}


def main() -> int:
    api_vars = _service_variables(API_SERVICE_ID)
    local = _normalize(_parse_env(BACKEND_ENV))
    source = _normalize({**local, **{k: v for k, v in api_vars.items() if v}})

    missing = [
        name for name in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "CRON_SECRET")
        if not source.get(name)
    ]
    if missing:
        print(f"❌ Eksik env (.env veya Railway api): {', '.join(missing)}")
        print("   SUPABASE_SECRET_KEY → SUPABASE_SERVICE_KEY olarak da kabul edilir.")
        return 1

    for name in SERVICE_NAMES:
        vars_payload = _build_vars(source, for_cron=(name == "cron"))
        print(f"Railway {name} env yazılıyor…")
        _railway_upsert(name, vars_payload)
        print(f"✓ {name}: SUPABASE_URL set, SERVICE_KEY set, USE_SUPABASE_DB=true")
        if name == "cron":
            print(f"  CRON_EXECUTION_MODE=direct, CRON_SKIP_PUSH={vars_payload.get('CRON_SKIP_PUSH')}")

    subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

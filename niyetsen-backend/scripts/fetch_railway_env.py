#!/usr/bin/env python3
"""Railway production env değerlerini okur; stdout'a SIR yazdırmaz."""
from __future__ import annotations

import json
import os
import pathlib
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
    raise RuntimeError(
        "RAILWAY_PROJECT_TOKEN yok. Geçici olarak export edin veya token dosyası oluşturun."
    )


def fetch_service_variables() -> dict[str, str]:
    body = json.dumps({
        "query": (
            "query($projectId:String!,$environmentId:String!,$serviceId:String!){"
            "variables(projectId:$projectId,environmentId:$environmentId,serviceId:$serviceId)"
            "}"
        ),
        "variables": {
            "projectId": PROJECT_ID,
            "environmentId": ENVIRONMENT_ID,
            "serviceId": API_SERVICE_ID,
        },
    }).encode()
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
    variables = payload["data"]["variables"]
    if not isinstance(variables, dict):
        raise RuntimeError("Beklenmeyen variables yanıtı")
    return variables


if __name__ == "__main__":
    names = sorted(fetch_service_variables())
    print("Railway API env anahtarları:", ", ".join(names))

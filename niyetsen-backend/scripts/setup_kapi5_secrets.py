#!/usr/bin/env python3
"""KAPI 5 — Railway + yerel .env için RevenueCat değişkenlerini ayarlar (sırları yazdırmaz)."""
from __future__ import annotations

import json
import pathlib
import secrets
import subprocess
import sys
import urllib.request

API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = "922f94cb-08ae-47ce-a44a-7527ff98c004"
ENVIRONMENT_ID = "73ba01c3-9c84-4343-9439-80cab9923991"
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN_FILE = ROOT / ".railway-project-token"
BACKEND_ENV = ROOT / ".env"
MOBILE_ENV = ROOT.parent / "mobile" / ".env"
MOBILE_DIR = ROOT.parent / "mobile"


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


def _upsert_env_key(path: pathlib.Path, key: str, value: str) -> None:
    if not path.exists():
        return
    lines = path.read_text().splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[index] = f"{key}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


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


def _eas_env(name: str, value: str) -> bool:
    if not value:
        return False
    proc = subprocess.run(
        [
            "npx",
            "eas-cli",
            "env:create",
            "production",
            "--name",
            name,
            "--value",
            value,
            "--visibility",
            "plaintext",
            "--type",
            "string",
            "--scope",
            "project",
            "--environment",
            "production",
            "--environment",
            "preview",
            "--environment",
            "development",
            "--force",
            "--non-interactive",
        ],
        cwd=MOBILE_DIR,
        capture_output=True,
        text=True,
    )
    combined = proc.stdout + proc.stderr
    if proc.returncode != 0 and "Created" not in combined and "updated" not in combined.lower():
        print(f"⚠️  EAS {name}: {proc.stderr.strip() or proc.stdout.strip()}")
        return False
    return True


def main() -> int:
    backend = _parse_env(BACKEND_ENV)
    mobile = _parse_env(MOBILE_ENV)

    webhook_secret = backend.get("REVENUECAT_WEBHOOK_SECRET") or secrets.token_urlsafe(32)
    rc_api_key = backend.get("REVENUECAT_API_KEY", "")
    entitlement = backend.get("REVENUECAT_ENTITLEMENT_ID") or mobile.get(
        "EXPO_PUBLIC_RC_ENTITLEMENT_ID", "premium"
    )

    ios_key = mobile.get("EXPO_PUBLIC_REVENUECAT_IOS_API_KEY") or mobile.get(
        "EXPO_PUBLIC_REVENUECAT_API_KEY", ""
    )
    android_key = mobile.get("EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY") or mobile.get(
        "EXPO_PUBLIC_REVENUECAT_API_KEY", ""
    )
    api_url = mobile.get(
        "EXPO_PUBLIC_API_URL", "https://api-production-86f1.up.railway.app"
    )

    railway_vars = {
        "REVENUECAT_WEBHOOK_SECRET": webhook_secret,
        "REVENUECAT_ENTITLEMENT_ID": entitlement,
    }
    if rc_api_key:
        railway_vars["REVENUECAT_API_KEY"] = rc_api_key

    print("Railway api servisine değişkenler yazılıyor…")
    _railway_upsert("api", railway_vars)
    print("✓ Railway REVENUECAT_* ayarlandı")

    _upsert_env_key(BACKEND_ENV, "REVENUECAT_WEBHOOK_SECRET", webhook_secret)
    _upsert_env_key(BACKEND_ENV, "REVENUECAT_ENTITLEMENT_ID", entitlement)
    if rc_api_key:
        _upsert_env_key(BACKEND_ENV, "REVENUECAT_API_KEY", rc_api_key)
    print("✓ niyetsen-backend/.env güncellendi")

    _upsert_env_key(MOBILE_ENV, "EXPO_PUBLIC_API_URL", api_url)
    _upsert_env_key(MOBILE_ENV, "EXPO_PUBLIC_RC_ENTITLEMENT_ID", entitlement)
    if ios_key:
        _upsert_env_key(MOBILE_ENV, "EXPO_PUBLIC_REVENUECAT_IOS_API_KEY", ios_key)
    if android_key:
        _upsert_env_key(MOBILE_ENV, "EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY", android_key)
    print("✓ mobile/.env güncellendi")

    eas_ok = 0
    eas_targets = [
        ("EXPO_PUBLIC_API_URL", api_url),
        ("EXPO_PUBLIC_RC_ENTITLEMENT_ID", entitlement),
        ("EXPO_PUBLIC_REVENUECAT_IOS_API_KEY", ios_key),
        ("EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY", android_key),
    ]
    for name, value in eas_targets:
        if _eas_env(name, value):
            eas_ok += 1
            print(f"✓ EAS secret: {name}")

    subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )

    missing: list[str] = []
    if not rc_api_key:
        missing.append("REVENUECAT_API_KEY (Railway — RevenueCat Project Settings > Secret API key)")
    if not ios_key:
        missing.append("EXPO_PUBLIC_REVENUECAT_IOS_API_KEY (RevenueCat > iOS app public key)")
    if not android_key:
        missing.append("EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY (RevenueCat > Android app public key)")

    print("\n--- Özet ---")
    print(f"REVENUECAT_WEBHOOK_SECRET: ayarlandı (RevenueCat webhook Authorization Bearer ile aynı olmalı)")
    print(f"REVENUECAT_ENTITLEMENT_ID: {entitlement}")
    print(f"EXPO_PUBLIC_API_URL: {api_url}")
    if missing:
        print("\n⚠️  Eksik — RevenueCat dashboard'dan alıp şunları .env'e yaz, scripti tekrar çalıştır:")
        for item in missing:
            print(f"   - {item}")
        return 1
    if eas_ok < len([v for _, v in eas_targets if v]):
        print("⚠️  Bazı EAS secret'ları yazılamadı — `npx eas-cli login` gerekebilir.")
        return 1
    print("✅ KAPI 5 secret kurulumu tamam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

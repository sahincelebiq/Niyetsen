#!/usr/bin/env python3
"""beforeShellExecution — Railway deploy korumaları (hafıza Tuzak #10).

- `railway up --service api` yalnız REPO KÖKÜNDEN (rootDirectory=niyetsen-backend
  Railway'de tanımlı; niyetsen-backend/ içinden koşulursa yol ikiye katlanır, build
  başlamadan FAILED).
- `railway up --service cron` yalnız `niyetsen-backend/` içinden (configFile
  /railway.cron.toml orada).
- `railway up` servis belirtmeden → sor.
- `accept-deploy` / `accept_deploy` → DENY (production'daki staged patch tüm
  env'leri ve api domain'ini siler; dashboard'dan discard edilmeli).

Çıktı: {"permission": "allow"|"ask"|"deny", "user_message", "agent_message"}.
Python 3.9 uyumlu. Hata durumunda fail-open (allow).
"""
from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT_MARKER = "NIYETSEN_MASTER_PLAN.md"


def _effective_cwd(command: str, cwd: str) -> str:
    """`cd X && …` ile başlıyorsa X'i hesaba kat."""
    m = re.match(r"\s*cd\s+([^\s;&|]+)\s*(?:&&|;)", command)
    if not m:
        return cwd
    target = os.path.expanduser(m.group(1).strip("'\""))
    return target if os.path.isabs(target) else os.path.normpath(os.path.join(cwd, target))


def decide(command: str, cwd: str) -> dict:
    lowered = command.lower()
    if "accept-deploy" in lowered or "accept_deploy" in lowered:
        return {
            "permission": "deny",
            "user_message": "accept-deploy ENGELLENDİ: production staged patch env'leri ve api domain'ini siler. Dashboard'dan discard et.",
            "agent_message": "Hook: `accept-deploy` yasak (hafıza Tuzak #10). Değişikliği Railway dashboard'dan discard et; CLI ile kabul etme.",
        }
    if not re.search(r"\brailway\s+up\b", lowered):
        return {"permission": "allow"}

    eff = _effective_cwd(command, cwd).rstrip("/")
    in_backend = eff.endswith("/niyetsen-backend")
    in_root = os.path.isfile(os.path.join(eff, REPO_ROOT_MARKER)) and not in_backend
    service = None
    m = re.search(r"--service[\s=]+([A-Za-z0-9_-]+)", command)
    if m:
        service = m.group(1).lower()

    if service == "api" and in_backend:
        return {
            "permission": "deny",
            "user_message": "railway up --service api niyetsen-backend/ içinden KOŞULMAZ (rootDirectory ikiye katlanır → FAILED). Repo kökünden koş.",
            "agent_message": "Hook: api deploy'u repo kökünden `railway up --project … --environment … --service api --ci` ile koş (Tuzak #10).",
        }
    if service == "cron" and not in_backend:
        return {
            "permission": "deny",
            "user_message": "railway up --service cron yalnız niyetsen-backend/ içinden koşulur (/railway.cron.toml orada).",
            "agent_message": "Hook: `cd niyetsen-backend && railway up --service cron --ci` (Tuzak #10).",
        }
    if service is None:
        return {
            "permission": "ask",
            "user_message": "railway up servis belirtmeden çalıştırılıyor — api mi cron mu? Yanlış servis/dizin canlıyı bozar.",
            "agent_message": "Hook: `--service api` (repo kökü) veya `--service cron` (niyetsen-backend/) belirt.",
        }
    if "--ci" not in lowered:
        return {
            "permission": "ask",
            "user_message": "railway up --ci olmadan log akışına takılabilir; --ci eklemen önerilir.",
            "agent_message": "Hook: `--ci` bayrağını ekle (deploy bitince çıkar).",
        }
    if service == "api" and not in_root:
        return {
            "permission": "ask",
            "user_message": f"api deploy'u repo kökü görünmeyen bir dizinden ({eff}) — emin misin?",
            "agent_message": "Hook: api için çalışma dizini repo kökü olmalı.",
        }
    return {"permission": "allow"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = str(payload.get("command", ""))
        cwd = str(payload.get("cwd") or payload.get("working_directory") or os.getcwd())
        print(json.dumps(decide(command, cwd), ensure_ascii=False))
    except Exception:
        print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

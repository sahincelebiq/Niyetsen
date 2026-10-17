#!/usr/bin/env python3
"""beforeMCPExecution — Railway MCP `accept-deploy` aracını engeller.

Production'daki bekleyen staged patch api/cron/MySQL'in tüm env'lerini ve api
domain'ini siler (hafıza Tuzak #10). CLI tarafı shell-guard.py'de; burası MCP.
Python 3.9 uyumlu, fail-open.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"permission": "allow"}))
        return 0
    name = " ".join(
        str(payload.get(k, "")) for k in ("tool_name", "toolName", "name", "tool")
    ).lower().replace("_", "-")
    if "accept-deploy" in name:
        print(
            json.dumps(
                {
                    "permission": "deny",
                    "user_message": "Railway accept-deploy ENGELLENDİ — staged patch env'leri siler; dashboard'dan discard et.",
                    "agent_message": "Hook: `accept-deploy` MCP aracı yasak (Tuzak #10). Değişikliği dashboard'dan discard et.",
                },
                ensure_ascii=False,
            )
        )
        return 0
    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

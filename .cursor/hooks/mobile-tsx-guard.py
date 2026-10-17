#!/usr/bin/env python3
"""afterFileEdit / postToolUse — mobil .ts/.tsx kalite tarayıcısı (V2 Faz 0).

Taranan ihlaller (hafıza Tuzak #1 + İlkbahar token kuralı + `any` yasağı):
  1. `Easing` / `Animated` 'react-native'ten import → Reanimated worklet crash.
  2. Hex renk hardcode (`#RGB`, `#RRGGBB`, `#RRGGBBAA`) — yalnız theme.ts /
     zodiac.ts gibi token dosyalarına izin var.
  3. TypeScript `any` (`: any`, `as any`, `<any>`, `any[]`).

Engellemez (afterFileEdit engelleyemez); bulguları `additional_context` ile
ajana döndürür ve stdout'a yazar. Python 3.9 uyumlu (macOS /usr/bin/python3).
"""
from __future__ import annotations

import json
import os
import re
import sys

ALLOW_HEX_FILES = (
    "src/constants/theme.ts",
    "src/constants/zodiac.ts",
    "src/constants/mystic-colors.ts",
)
HEX_RE = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
ANY_RE = re.compile(
    r"(?::\s*any\b(?![\w.\[]))|(?::\s*any\[\])|(?<![\w.])as\s+any\b|<any>|(?<![\w.])\bany\[\]"
)
RN_IMPORT_RE = re.compile(
    r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]", re.MULTILINE
)
TEST_OR_COMMENT_HINT = re.compile(r"^\s*(//|\*|/\*)")


def _file_path(payload: dict) -> str:
    for key in ("file_path", "path", "target_file", "filePath"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if isinstance(tool_input, dict):
        for key in ("path", "file_path", "target_file"):
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def scan(path: str, text: str) -> list[str]:
    findings: list[str] = []
    norm = path.replace("\\", "/")
    for match in RN_IMPORT_RE.finditer(text):
        names = {n.strip().split(" as ")[0] for n in match.group(1).split(",")}
        bad = sorted(n for n in names if n in ("Easing", "Animated"))
        if bad:
            findings.append(
                f"Reanimated kuralı: {', '.join(bad)} 'react-native'ten import edilmiş → "
                "'react-native-reanimated' kullan (worklet crash)."
            )
    if not any(norm.endswith(allow) for allow in ALLOW_HEX_FILES):
        for i, line in enumerate(text.splitlines(), 1):
            if TEST_OR_COMMENT_HINT.match(line):
                continue
            for hx in HEX_RE.findall(line):
                findings.append(f"satır {i}: hex hardcode {hx} → theme.ts token'ı kullan.")
    for i, line in enumerate(text.splitlines(), 1):
        if TEST_OR_COMMENT_HINT.match(line):
            continue
        if ANY_RE.search(line):
            findings.append(f"satır {i}: TypeScript `any` → somut tip yaz.")
    return findings[:12]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    path = _file_path(payload)
    norm = path.replace("\\", "/")
    if not norm or not norm.endswith((".ts", ".tsx")) or "/mobile/" not in norm and not norm.startswith("mobile/"):
        return 0
    if norm.endswith((".d.ts", ".test.ts", ".test.tsx")):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return 0
    findings = scan(path, text)
    if not findings:
        return 0
    rel = os.path.relpath(path, os.getcwd()) if os.path.isabs(path) else path
    message = f"[niyetsen-hook] {rel}: {len(findings)} kalite bulgusu\n- " + "\n- ".join(findings)
    print(json.dumps({"additional_context": message}, ensure_ascii=False))
    print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

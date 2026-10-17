#!/usr/bin/env python3
"""beforeSubmitPrompt — sır deseni engeli (V2 Faz 0, CLAUDE.md "sırlar yalnız .env").

Prompt'ta API anahtarı / JWT / şifreli DSN / özel anahtar görülürse gönderim
durdurulur; kullanıcıya hangi desenin yakalandığı söylenir (değer gösterilmez).
Chat'e düşen anahtar transkriptte kalır → rotasyon şarttır.

Çıktı: {"continue": false, "user_message": "..."} ya da {"continue": true}.
Python 3.9 uyumlu, fail-open.
"""
from __future__ import annotations

import json
import re
import sys

PATTERNS = [
    ("Google API anahtarı", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("OpenAI/Manus/RC tarzı sk- anahtarı", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("Supabase secret / PAT", re.compile(r"\b(?:sb_secret_|sbp_)[A-Za-z0-9_\-]{10,}\b")),
    ("Vercel API anahtarı", re.compile(r"\bvck_[A-Za-z0-9]{20,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("şifreli Postgres DSN", re.compile(r"postgres(?:ql)?://[^\s:/@]+:(?!\[YOUR-PASSWORD\]|\*\*\*|<)[^\s@]{4,}@")),
    ("özel anahtar bloğu", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----")),
    ("RevenueCat secret", re.compile(r"\bsk_[A-Za-z0-9]{20,}\b")),
]


def findings(text: str) -> list[str]:
    hits = []
    for label, pattern in PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        text = str(payload.get("prompt") or payload.get("text") or "")
        hits = findings(text)
    except Exception:
        print(json.dumps({"continue": True}))
        return 0
    if not hits:
        print(json.dumps({"continue": True}))
        return 0
    print(
        json.dumps(
            {
                "continue": False,
                "user_message": (
                    "Prompt'ta sır deseni yakalandı: "
                    + ", ".join(hits)
                    + ". Değeri chat'e yapıştırma — .env'e yaz (gitignore'da) ve bu anahtar "
                    "zaten paylaşıldıysa ROTASYON yap. Sonra prompt'u değersiz gönder."
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

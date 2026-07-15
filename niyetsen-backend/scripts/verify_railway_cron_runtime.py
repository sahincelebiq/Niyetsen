#!/usr/bin/env python3
"""Railway cron log/doğrulama rehberi — direct mod mu HTTP (uvicorn) mod mu?"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CRON_TOML = ROOT / "railway.cron.toml"
CRON_SCRIPT = ROOT / "scripts" / "run_scheduled_jobs.py"


def main() -> int:
    issues: list[str] = []
    tips: list[str] = []

    if not CRON_SCRIPT.exists():
        issues.append("scripts/run_scheduled_jobs.py bulunamadı")
    else:
        body = CRON_SCRIPT.read_text()
        if "cron modu: direct" not in body:
            issues.append("run_scheduled_jobs.py direct mod logu içermiyor")
        if "httpx.post" in body or "API_BASE_URL" in body:
            issues.append("run_scheduled_jobs.py hâlâ HTTP cron çağrısı içeriyor")

    if CRON_TOML.exists():
        toml = CRON_TOML.read_text()
        if "run_scheduled_jobs.py" not in toml:
            issues.append("railway.cron.toml startCommand run_scheduled_jobs.py değil")
        if "cron_paused.py" in toml:
            issues.append("railway.cron.toml hâlâ cron_paused.py kullanıyor")
    else:
        issues.append("railway.cron.toml eksik")

    tips.extend([
        "Railway cron servisi → Settings → Config-as-code: /railway.cron.toml",
        "Doğru log: 'cron modu: direct' + 'close-day: {...}' + 'cron tamamlandı (exit 0)'",
        "Yanlış log: 'POST /cron/close-day HTTP/1.1' → uvicorn çalışıyor (railway.toml kullanılıyor)",
        "Env: CRON_EXECUTION_MODE=direct, USE_SUPABASE_DB=true, CRON_SKIP_PUSH=true (ilk stabil tur)",
    ])

    if issues:
        print("❌ Cron runtime sorunları:")
        for item in issues:
            print(f"  - {item}")
    else:
        print("✅ Repo tarafı direct-only cron için hazır")

    print("\nRailway kontrol listesi:")
    for item in tips:
        print(f"  • {item}")

    try:
        from scripts.verify_cron_config import main as verify_env

        print()
        env_code = verify_env()
        if env_code != 0:
            return env_code
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Railway env doğrulaması atlandı: {exc}")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())

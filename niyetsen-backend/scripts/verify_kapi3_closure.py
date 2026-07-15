#!/usr/bin/env python3
"""
KAPI 3 kapanış doğrulaması — otomatik kontroller.
Plan §5: Railway cron + Supabase + görev/kanıt/puan zinciri.

Kullanım:
    cd niyetsen-backend
    python -m scripts.verify_kapi3_closure
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

KAPI3_TEST_FILES = [
    "tests/test_task_lifecycle.py",
    "tests/test_scoring.py",
    "tests/test_consent.py",
    "tests/test_cron_direct.py",
    "tests/test_chat_guardrails.py",
    "tests/test_bonus_notifications.py",
]


def _run_pytest(files: list[str]) -> bool:
    cmd = [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "-q", "--tb=no", *files]
    print("→ KAPI 3 test paketi…")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (result.stdout or result.stderr).strip().splitlines()[-3:]
    for line in tail:
        print(f"  {line}")
    return result.returncode == 0


def _run_cron_runtime_check() -> bool:
    print("→ Cron runtime (repo + Railway env)…")
    result = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "scripts.verify_railway_cron_runtime"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(result.stdout or result.stderr)
    return result.returncode == 0


def _run_supabase_smoke() -> bool:
    from app.config import settings

    if not settings.USE_SUPABASE_DB:
        print("⚠️  USE_SUPABASE_DB=false — Supabase smoke atlandı (lokal dev)")
        return True
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        print("❌ Supabase URL/service key eksik")
        return False

    print("→ Supabase prod smoke test…")
    result = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "scripts.smoke_test_supabase"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = (result.stdout or "") + (result.stderr or "")
        print(err[-1200:])
        return False
    if "Tüm Supabase round-trip testleri geçti" in (result.stdout or ""):
        print("  OK — round-trip geçti")
        return True
    print((result.stdout or result.stderr)[-800:])
    return result.returncode == 0


def _run_close_due_dry() -> bool:
    """Prod Supabase'te close_due_users — yazma yapar, exit 0 beklenir."""
    from app.config import settings

    if not settings.USE_SUPABASE_DB:
        print("⚠️  close_due_users prod dry-run atlandı")
        return True

    print("→ close_due_users (prod Supabase)…")
    result = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "scripts" / "run_scheduled_jobs.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "CRON_SKIP_PUSH": "true"},
    )
    out = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        print(out[-1200:])
        return False
    if "cron tamamlandı (exit 0)" not in out:
        print(out[-1200:])
        return False
    if "close-day" in out:
        print("  OK — direct cron close-day çalıştı")
        return True
    print(out[-800:])
    return False


def _master_plan_marked_closed() -> bool:
    plan = (ROOT.parent / "NIYETSEN_MASTER_PLAN.md").read_text()
    ok = "KAPI 3:** ✅ **KAPANDI" in plan or "KAPI 3:** ✅" in plan
    if ok:
        print("→ NIYETSEN_MASTER_PLAN.md KAPI 3 kapalı işaretli")
    else:
        print("❌ MASTER_PLAN KAPI 3 henüz kapalı işaretli değil")
    return ok


def main() -> int:
    checks: list[tuple[str, bool]] = []

    checks.append(("pytest KAPI3 paketi", _run_pytest(KAPI3_TEST_FILES)))
    checks.append(("cron runtime", _run_cron_runtime_check()))
    checks.append(("supabase smoke", _run_supabase_smoke()))
    checks.append(("cron close-day prod", _run_close_due_dry()))
    checks.append(("master plan işareti", _master_plan_marked_closed()))

    print("\n--- KAPI 3 kapanış özeti ---")
    failed = []
    for name, ok in checks:
        mark = "✅" if ok else "❌"
        print(f"{mark} {name}")
        if not ok:
            failed.append(name)

    if failed:
        print(f"\n❌ KAPI 3 kapanış tamamlanamadı: {', '.join(failed)}")
        return 1

    print("\n✅ KAPI 3 kapanış kriterleri otomatik doğrulandı.")
    print("   Elle: gerçek cihazda foto→puan→rank bir kez daha gözle kontrol (Expo Go).")
    print("   Railway: cron logunda 'cron modu: direct' görünmeli (config-as-code: railway.cron.toml).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

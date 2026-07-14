#!/usr/bin/env python3
"""Railway cron servisini yeniden deploy eder (duraklatma sonrası)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Cron servisi redeploy (cron_paused.py aktif olmalı)…")
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

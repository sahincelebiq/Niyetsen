#!/usr/bin/env python3
"""Railway cron'u devam ettir — run_scheduled_jobs.py + cron redeploy."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRON_TOML = ROOT / "railway.cron.toml"
ACTIVE = 'startCommand = "python scripts/run_scheduled_jobs.py"'


def _set_active() -> None:
    text = CRON_TOML.read_text()
    new_text, n = re.subn(
        r'startCommand = "python scripts/cron_paused\.py"',
        ACTIVE,
        text,
        count=1,
    )
    if n == 0 and ACTIVE not in text:
        raise RuntimeError("railway.cron.toml startCommand güncellenemedi")
    CRON_TOML.write_text(new_text if n else text)


def main() -> int:
    _set_active()
    print("✓ railway.cron.toml → run_scheduled_jobs.py")
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.railway_redeploy"],
        cwd=ROOT,
        check=False,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

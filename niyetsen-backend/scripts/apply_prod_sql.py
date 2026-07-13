#!/usr/bin/env python3
"""RUN_IN_SUPABASE_SQL_EDITOR.sql içeriğini prod Postgres'e uygular."""
from __future__ import annotations

import os
import pathlib
import re
import sys

from scripts.fetch_railway_env import fetch_service_variables

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "supabase" / "migrations" / "RUN_IN_SUPABASE_SQL_EDITOR.sql"


def _service_key() -> tuple[str, str]:
    env = fetch_service_variables()
    url = env.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE credentials eksik")
    return url, key


def _statements(sql: str) -> list[str]:
    lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    parts = [part.strip() for part in re.split(r";\s*\n", body) if part.strip()]
    return [f"{part};" for part in parts]


def main() -> int:
    try:
        import psycopg2  # type: ignore
    except ImportError:
        print("❌ psycopg2 yüklü değil: pip install psycopg2-binary")
        return 1

    db_url = os.environ.get("SUPABASE_DB_URL", "")
    if not db_url:
        print("❌ SUPABASE_DB_URL gerekli (Supabase → Settings → Database → URI)")
        print("   Örnek: postgresql://postgres.[ref]:[PASSWORD]@...pooler.supabase.com:6543/postgres")
        return 1

    sql = SQL_PATH.read_text()
    statements = _statements(sql)
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
                print(f"✓ {stmt.splitlines()[0][:72]}...")
    finally:
        conn.close()
    print(f"✅ {len(statements)} SQL ifadesi uygulandı")
    return 0


if __name__ == "__main__":
    sys.exit(main())

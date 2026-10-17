"""Günlük `pg_dump` yedeği → S3-uyumlu kova (V2 §7.1 madde 2).

Kullanım:
  python -m scripts.backup_pg_dump            # cron: saat uygunsa ve bugün yoksa al
  python -m scripts.backup_pg_dump --force    # hemen al (saat/bugün kontrolü yok)
  python -m scripts.backup_pg_dump --dry-run  # komutları göster, çalıştırma

Env (Railway `cron` servisi):
  BACKUP_DATABASE_URL  (yoksa DIRECT_URL — session pooler 5432; transaction
                        pooler 6543 pg_dump ile ÇALIŞMAZ)
  BACKUP_S3_ENDPOINT, BACKUP_S3_BUCKET, BACKUP_S3_ACCESS_KEY, BACKUP_S3_SECRET_KEY
  BACKUP_S3_REGION=auto  BACKUP_PREFIX=niyetsen/pg  BACKUP_RETENTION_DAYS=30
  BACKUP_SCHEMAS=public,auth,storage  BACKUP_HOUR_UTC=1  BACKUP_VERIFY_MD5=true

Çıktı: `<prefix>/YYYY/MM/DD/niyetsen-<ts>Z.dump` + `.manifest.json`
(sha256, boyut, sürümler, tablo satır sayısı + md5 anlık görüntüsü).
Cron içinde `run_daily()` asla exception fırlatmaz; sonuç sözlüğü döner.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.backup import (  # noqa: E402
    BackupConfig,
    build_manifest,
    build_object_key,
    day_prefix,
    is_backup_due,
    manifest_key,
    mask_dsn,
    pg_dump_command,
    select_expired_keys,
    sha256_file,
    take_snapshot,
)
from scripts import backup_io  # noqa: E402


def perform_backup(cfg: BackupConfig, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Tek yedek turu: dump → snapshot → manifest → upload → prune."""
    now = now or datetime.now(timezone.utc)
    dump_key = build_object_key(cfg.prefix, now)
    cmd_preview = pg_dump_command(cfg.database_url, cfg.schemas, "<tmp>/niyetsen.dump")
    if dry_run:
        return {
            "status": "dry_run",
            "dump_key": dump_key,
            "pg_dump": " ".join(mask_dsn(p) for p in cmd_preview),
            "db": mask_dsn(cfg.database_url),
        }

    client = backup_io.s3_client(cfg)
    with tempfile.TemporaryDirectory(prefix="niyetsen-backup-") as tmp:
        dump_path = Path(tmp) / "niyetsen.dump"
        backup_io.run_pg_dump(pg_dump_command(cfg.database_url, cfg.schemas, dump_path), cfg.database_url)
        size = dump_path.stat().st_size
        digest = sha256_file(dump_path)

        snapshot = take_snapshot(
            backup_io.psql_runner(cfg.database_url), cfg.schemas, verify_md5=cfg.verify_md5, now=now
        )
        manifest = build_manifest(
            dump_key=dump_key,
            dump_size=size,
            dump_sha256=digest,
            snapshot=snapshot,
            pg_dump_version=backup_io.tool_version("pg_dump"),
            server_version=backup_io.server_version(cfg.database_url),
            schemas=cfg.schemas,
        )
        manifest_path = Path(tmp) / "niyetsen.manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        backup_io.upload_file(client, cfg.s3_bucket, dump_key, dump_path, content_type="application/octet-stream")
        backup_io.upload_file(
            client, cfg.s3_bucket, manifest_key(dump_key), manifest_path, content_type="application/json"
        )

    expired = select_expired_keys(
        backup_io.list_objects(client, cfg.s3_bucket, cfg.prefix.rstrip("/") + "/"), now, cfg.retention_days
    )
    pruned = backup_io.delete_objects(client, cfg.s3_bucket, expired) if expired else 0

    return {
        "status": "done",
        "dump_key": dump_key,
        "size_bytes": size,
        "sha256": digest[:16] + "…",
        "tables": len(snapshot.tables),
        "rows": snapshot.total_rows,
        "pruned": pruned,
    }


def run_daily(*, env: dict[str, str] | None = None, now: datetime | None = None, force: bool = False) -> dict[str, Any]:
    """Cron girişi — hiçbir koşulda exception fırlatmaz.

    Dönüş `status`: not_configured | skipped | done | error
    """
    env = env if env is not None else dict(os.environ)
    now = now or datetime.now(timezone.utc)
    missing = BackupConfig.missing(env)
    if missing:
        return {"status": "not_configured", "missing": missing}
    cfg = BackupConfig.from_env(env)
    assert cfg is not None
    try:
        if not force:
            client = backup_io.s3_client(cfg)
            already = bool(backup_io.list_objects(client, cfg.s3_bucket, day_prefix(cfg.prefix, now)))
            if not is_backup_due(now, cfg.hour_utc, already):
                return {
                    "status": "skipped",
                    "reason": "already_today" if already else f"hour_utc!={cfg.hour_utc}",
                }
        return perform_backup(cfg, now=now)
    except Exception as exc:  # noqa: BLE001 — cron zırhı
        traceback.print_exc()
        return {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="saat/bugün kontrolü olmadan hemen al")
    parser.add_argument("--dry-run", action="store_true", help="komutları göster, çalıştırma")
    parser.add_argument("--strict", action="store_true", help="yapılandırma eksikse sıfır dışı çık")
    args = parser.parse_args(argv)

    env = backup_io.env_with_dotenv()
    missing = BackupConfig.missing(env)
    if missing:
        print("yedek yapılandırılmamış — eksik: " + ", ".join(missing))
        return 1 if args.strict else 0
    cfg = BackupConfig.from_env(env)
    assert cfg is not None

    if args.dry_run:
        result = perform_backup(cfg, dry_run=True)
    else:
        result = run_daily(env=env, force=args.force)
    print("backup: " + json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") in ("done", "skipped", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())

"""Yedek I/O yardımcıları — subprocess (pg_dump/pg_restore/psql) + S3.

`app/core/backup.py` saf mantık; burası dış dünya. Tüm fonksiyonlar DSN'i
loglarken `mask_dsn` kullanır. boto3 tembel import edilir (API imajında
yedek kodu yüklenmez).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.backup import BackupConfig, mask_dsn  # noqa: E402


class BackupToolError(RuntimeError):
    """pg_dump/psql/pg_restore bulunamadı ya da sıfır dışı çıktı."""


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BackupToolError(
            f"{name} bulunamadı — Dockerfile.cron postgresql-client-17 kurar; "
            "yerelde `brew install postgresql@17`."
        )
    return path


def tool_version(name: str) -> str:
    try:
        out = subprocess.run([name, "--version"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "?"


def _pg_env() -> dict[str, str]:
    """Anlık görüntü metni oturum saat dilimine bağlıdır. Kaynak (Supabase) ve
    hedef (yerel) aynı dilimde olmazsa md5 tutmaz, satırlar eşit olsa bile."""
    env = os.environ.copy()
    env["PGOPTIONS"] = "-c timezone=UTC -c datestyle=ISO,MDY"
    return env


def run_command(cmd: list[str], *, dsn: str | None = None, timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    """Komutu çalıştırır; hata mesajında DSN maskelenir."""
    shown = [mask_dsn(part) if dsn and dsn in part else part for part in cmd]
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False, env=_pg_env()
        )
    except subprocess.TimeoutExpired as exc:
        raise BackupToolError(f"zaman aşımı ({timeout}s): {' '.join(shown)}") from exc


def psql_runner(dsn: str):
    """`run_sql(sql) -> list[list[str]]` — psql -At, sekme ayraçlı."""
    require_binary("psql")

    def run_sql(sql: str) -> list[list[str]]:
        proc = run_command(
            [
                "psql",
                "--no-psqlrc",
                "--tuples-only",
                "--no-align",
                "--field-separator=\t",
                "--set=ON_ERROR_STOP=1",
                f"--dbname={dsn}",
                "--command",
                sql,
            ],
            dsn=dsn,
            timeout=600,
        )
        if proc.returncode != 0:
            raise BackupToolError(
                f"psql hata ({proc.returncode}) [{mask_dsn(dsn)}]: {proc.stderr.strip()[:400]}"
            )
        rows: list[list[str]] = []
        for line in proc.stdout.splitlines():
            if line == "":
                continue
            rows.append(line.split("\t"))
        return rows

    return run_sql


def server_version(dsn: str) -> str:
    try:
        rows = psql_runner(dsn)("show server_version")
        return rows[0][0] if rows and rows[0] else "?"
    except BackupToolError:
        return "?"


def run_pg_dump(cmd: list[str], dsn: str) -> None:
    require_binary("pg_dump")
    proc = run_command(cmd, dsn=dsn)
    if proc.returncode != 0:
        raise BackupToolError(f"pg_dump hata ({proc.returncode}): {proc.stderr.strip()[:600]}")


def run_pg_restore(cmd: list[str], dsn: str) -> tuple[int, str]:
    """pg_restore hata saysa da devam eder; (dönüş kodu, stderr) verir."""
    require_binary("pg_restore")
    proc = run_command(cmd, dsn=dsn)
    return proc.returncode, proc.stderr


def run_psql_script(dsn: str, sql: str) -> None:
    require_binary("psql")
    proc = subprocess.run(
        ["psql", "--no-psqlrc", "--set=ON_ERROR_STOP=1", f"--dbname={dsn}"],
        input=sql,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BackupToolError(f"psql script hata: {proc.stderr.strip()[:400]}")


# --------------------------------------------------------------------------
# S3-uyumlu depo (Cloudflare R2 / Backblaze B2 / MinIO / AWS)
# --------------------------------------------------------------------------

def s3_client(cfg: BackupConfig):
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError as exc:  # pragma: no cover - requirements'ta var
        raise BackupToolError("boto3 yüklü değil (requirements.txt)") from exc

    # S3-uyumlu sağlayıcılar (R2/B2/MinIO) boto3 ≥1.36'nın varsayılan CRC32
    # checksum başlıklarını reddedebilir → yalnız gerektiğinde hesapla.
    return boto3.client(
        "s3",
        endpoint_url=cfg.s3_endpoint,
        aws_access_key_id=cfg.s3_access_key,
        aws_secret_access_key=cfg.s3_secret_key,
        region_name=cfg.s3_region,
        config=BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def list_objects(client, bucket: str, prefix: str) -> list[tuple[str, datetime]]:
    objects: list[tuple[str, datetime]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []) or []:
            objects.append((item["Key"], item["LastModified"]))
    return objects


def upload_file(client, bucket: str, key: str, path: Path, *, content_type: str) -> None:
    client.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})


def download_file(client, bucket: str, key: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(path))


def delete_objects(client, bucket: str, keys: list[str]) -> int:
    deleted = 0
    for start in range(0, len(keys), 1000):
        chunk = keys[start : start + 1000]
        if not chunk:
            continue
        client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True})
        deleted += len(chunk)
    return deleted


def env_with_dotenv() -> dict[str, str]:
    """Yerel `.env` varsa yükle (cron'da Railway env zaten dolu)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(_ROOT / ".env")
    except ImportError:
        pass
    return dict(os.environ)


def summarize(payload: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in payload.items())

"""Yedek / geri yükleme çekirdeği — V2 §7.1 "veri kaybı önlem kapısı".

Saf mantık burada yaşar (test edilebilir, I/O yok):
- yedek konfigürasyonu (env → BackupConfig),
- nesne anahtarı / saklama süresi hesapları,
- pg_dump / pg_restore komut satırları,
- tablo satır sayısı + md5 anlık görüntüsü (snapshot) ve iki anlık görüntünün
  karşılaştırılması.

I/O (subprocess, S3) `scripts/backup_pg_dump.py` ve `scripts/verify_backup.py`
içindedir; onlar bu modülü kullanır. Sır (DSN şifresi) hiçbir log satırına
tam haliyle yazılmaz — `mask_dsn` kullan.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Supabase'in beklediği roller — hedef Postgres'te yoksa policy/grant
# ifadeleri pg_restore'da hata verir. Tatbikat öncesi NOLOGIN olarak açılır.
SUPABASE_ROLES: tuple[str, ...] = (
    "anon",
    "authenticated",
    "service_role",
    "authenticator",
    "supabase_admin",
    "supabase_auth_admin",
    "supabase_storage_admin",
    "dashboard_user",
)

DEFAULT_SCHEMAS: tuple[str, ...] = ("public", "auth", "storage")
DEFAULT_PREFIX = "niyetsen/pg"
DEFAULT_RETENTION_DAYS = 30
DEFAULT_HOUR_UTC = 1  # 04:00 İstanbul — gün kapanışları (23:59 TZ) bitmiş olur
MD5_MAX_ROWS = 500_000  # üstünde md5 atlanır (bellek); satır sayısı yine karşılaştırılır

_SQL_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class BackupConfig:
    database_url: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str = "auto"
    prefix: str = DEFAULT_PREFIX
    retention_days: int = DEFAULT_RETENTION_DAYS
    schemas: tuple[str, ...] = DEFAULT_SCHEMAS
    hour_utc: int = DEFAULT_HOUR_UTC
    verify_md5: bool = True

    @staticmethod
    def missing(env: Mapping[str, str]) -> list[str]:
        """Eksik zorunlu değişkenler; boş liste = yedek alınabilir."""
        missing: list[str] = []
        if not _first(env, "BACKUP_DATABASE_URL", "DIRECT_URL"):
            missing.append("BACKUP_DATABASE_URL (veya DIRECT_URL)")
        for name in ("BACKUP_S3_ENDPOINT", "BACKUP_S3_BUCKET", "BACKUP_S3_ACCESS_KEY", "BACKUP_S3_SECRET_KEY"):
            if not env.get(name, "").strip():
                missing.append(name)
        return missing

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "BackupConfig | None":
        if cls.missing(env):
            return None
        schemas = tuple(
            s.strip() for s in env.get("BACKUP_SCHEMAS", ",".join(DEFAULT_SCHEMAS)).split(",") if s.strip()
        ) or DEFAULT_SCHEMAS
        return cls(
            database_url=_first(env, "BACKUP_DATABASE_URL", "DIRECT_URL"),
            s3_endpoint=env["BACKUP_S3_ENDPOINT"].strip(),
            s3_bucket=env["BACKUP_S3_BUCKET"].strip(),
            s3_access_key=env["BACKUP_S3_ACCESS_KEY"].strip(),
            s3_secret_key=env["BACKUP_S3_SECRET_KEY"].strip(),
            s3_region=env.get("BACKUP_S3_REGION", "auto").strip() or "auto",
            prefix=env.get("BACKUP_PREFIX", DEFAULT_PREFIX).strip().strip("/") or DEFAULT_PREFIX,
            retention_days=_int(env, "BACKUP_RETENTION_DAYS", DEFAULT_RETENTION_DAYS),
            schemas=schemas,
            hour_utc=_int(env, "BACKUP_HOUR_UTC", DEFAULT_HOUR_UTC) % 24,
            verify_md5=env.get("BACKUP_VERIFY_MD5", "true").strip().lower() in ("1", "true", "yes"),
        )


def _first(env: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# --------------------------------------------------------------------------
# DSN / anahtar / zamanlama
# --------------------------------------------------------------------------

def mask_dsn(dsn: str) -> str:
    """`postgresql://user:şifre@host/db` → şifre `***`. Log güvenliği."""
    return re.sub(r"(://[^:/@]+:)[^@]*(@)", r"\1***\2", dsn)


def build_object_key(prefix: str, ts: datetime) -> str:
    """`niyetsen/pg/2026/10/17/niyetsen-20261017T010203Z.dump` (UTC)."""
    ts = ts.astimezone(timezone.utc)
    return (
        f"{prefix.strip('/')}/{ts:%Y/%m/%d}/niyetsen-{ts:%Y%m%dT%H%M%S}Z.dump"
    )


def manifest_key(dump_key: str) -> str:
    return dump_key + ".manifest.json"


def day_prefix(prefix: str, ts: datetime) -> str:
    ts = ts.astimezone(timezone.utc)
    return f"{prefix.strip('/')}/{ts:%Y/%m/%d}/"


def is_backup_due(now_utc: datetime, hour_utc: int, already_today: bool) -> bool:
    """Cron 5 dk'da bir tetiklenir; yedek günde bir, belirlenen UTC saatinde.

    `already_today` = bugünün önekinde nesne var (S3 listesi) → tekrar alma.
    Saat penceresi 1 saattir: cron o saat içinde bir kez başarır, sonrası atlanır.
    """
    if already_today:
        return False
    return now_utc.astimezone(timezone.utc).hour == hour_utc % 24


def select_expired_keys(
    objects: Iterable[tuple[str, datetime]], now_utc: datetime, retention_days: int
) -> list[str]:
    """Saklama süresi dolan nesne anahtarları (LastModified bazlı)."""
    if retention_days <= 0:
        return []
    cutoff = now_utc.astimezone(timezone.utc) - timedelta(days=retention_days)
    expired: list[str] = []
    for key, modified in objects:
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=timezone.utc)
        if modified < cutoff:
            expired.append(key)
    return sorted(expired)


# --------------------------------------------------------------------------
# pg_dump / pg_restore komutları
# --------------------------------------------------------------------------

def pg_dump_command(dsn: str, schemas: Iterable[str], out_path: Path | str) -> list[str]:
    """`--format=custom` (pg_restore ile seçici geri yükleme), sahiplik/yetki yok
    (hedef sunucuda Supabase rolleri olmayabilir)."""
    cmd = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--no-comments",
        f"--file={out_path}",
    ]
    for schema in schemas:
        _check_ident(schema)
        cmd.append(f"--schema={schema}")
    cmd.append(f"--dbname={dsn}")
    return cmd


def pg_restore_command(dsn: str, dump_path: Path | str, *, jobs: int = 2) -> list[str]:
    """Boş hedefe geri yükleme; hata olsa da devam eder (sonuç snapshot ile ölçülür)."""
    return [
        "pg_restore",
        "--no-owner",
        "--no-privileges",
        f"--jobs={max(1, jobs)}",
        f"--dbname={dsn}",
        str(dump_path),
    ]


def prepare_target_sql(roles: Iterable[str] = SUPABASE_ROLES) -> str:
    """Hedef Postgres'te Supabase rollerini (NOLOGIN) ve temel uzantıları aç.

    Policy/grant ifadeleri bu rolleri referans alır; yoksa pg_restore hata
    sayar. Uzantılar: `pgcrypto` (gen_random_uuid eski sürümler), `uuid-ossp`
    (auth.users varsayılanları). Superuser gerektirir — tatbikat ortamı yerel.
    """
    lines = [
        "create schema if not exists extensions;",
        'create extension if not exists "uuid-ossp" with schema extensions;',
        "create extension if not exists pgcrypto with schema extensions;",
    ]
    for role in roles:
        _check_ident(role)
        lines.append(
            "do $$ begin if not exists (select 1 from pg_roles where rolname = '"
            + role
            + "') then create role "
            + role
            + " nologin; end if; end $$;"
        )
    return "\n".join(lines) + "\n"


def _check_ident(name: str) -> None:
    if not _SQL_IDENT.match(name):
        raise ValueError(f"geçersiz SQL tanımlayıcı: {name!r}")


# --------------------------------------------------------------------------
# Snapshot: tablo başına satır sayısı + md5
# --------------------------------------------------------------------------

RunSql = Callable[[str], list[list[str]]]
"""`run_sql(sql) -> satırlar` — her satır sütun metinleri listesi.
Üretimde `psql -At -F'\t'` ile beslenir; testlerde sahte fonksiyon."""


def list_tables_sql(schema: str) -> str:
    _check_ident(schema)
    return (
        "select table_name from information_schema.tables "
        f"where table_schema = '{schema}' and table_type = 'BASE TABLE' "
        "order by table_name"
    )


def count_sql(schema: str, table: str) -> str:
    _check_ident(schema)
    _check_ident(table)
    return f'select count(*) from "{schema}"."{table}"'


def md5_sql(schema: str, table: str) -> str:
    """Satırları metne çevirip sıralı birleştirir; boş tablo → md5('')."""
    _check_ident(schema)
    _check_ident(table)
    # COLLATE "C" şart: kaynak (Supabase) ve hedef (yerel initdb) farklı
    # collation kullanırsa aynı satırlar farklı sırada birleşir ve md5 tutmaz.
    return (
        "select md5(coalesce(string_agg(t::text, E'\\n' order by t::text collate \"C\"), '')) "
        f'from "{schema}"."{table}" t'
    )


@dataclass
class TableStat:
    rows: int
    md5: str | None = None  # None = atlandı (çok büyük / kapalı)


@dataclass
class Snapshot:
    taken_at: str
    schemas: list[str]
    tables: dict[str, TableStat] = field(default_factory=dict)  # "schema.table"

    def to_dict(self) -> dict[str, Any]:
        return {
            "taken_at": self.taken_at,
            "schemas": list(self.schemas),
            "tables": {k: asdict(v) for k, v in sorted(self.tables.items())},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Snapshot":
        tables = {
            name: TableStat(rows=int(stat["rows"]), md5=stat.get("md5"))
            for name, stat in (data.get("tables") or {}).items()
        }
        return cls(
            taken_at=str(data.get("taken_at", "")),
            schemas=list(data.get("schemas") or []),
            tables=tables,
        )

    @property
    def total_rows(self) -> int:
        return sum(stat.rows for stat in self.tables.values())


def take_snapshot(
    run_sql: RunSql,
    schemas: Iterable[str],
    *,
    verify_md5: bool = True,
    md5_max_rows: int = MD5_MAX_ROWS,
    now: datetime | None = None,
) -> Snapshot:
    """Her şemadaki tüm tabloların satır sayısı (+ md5) — kaynak ve hedefte
    aynı fonksiyon koşar, çıktılar `compare_snapshots` ile kıyaslanır."""
    now = now or datetime.now(timezone.utc)
    snap = Snapshot(taken_at=now.astimezone(timezone.utc).isoformat(), schemas=list(schemas))
    for schema in schemas:
        for row in run_sql(list_tables_sql(schema)):
            if not row or not row[0]:
                continue
            table = row[0]
            count_rows = run_sql(count_sql(schema, table))
            rows = int(count_rows[0][0]) if count_rows and count_rows[0] else 0
            digest: str | None = None
            if verify_md5 and rows <= md5_max_rows:
                md5_rows = run_sql(md5_sql(schema, table))
                digest = md5_rows[0][0] if md5_rows and md5_rows[0] else None
            snap.tables[f"{schema}.{table}"] = TableStat(rows=rows, md5=digest)
    return snap


@dataclass(frozen=True)
class Diff:
    table: str
    kind: str  # missing_in_target | extra_in_target | row_count | md5
    source: str
    target: str

    def __str__(self) -> str:  # pragma: no cover - biçim
        return f"{self.table}: {self.kind} (kaynak={self.source}, hedef={self.target})"


def compare_snapshots(source: Snapshot, target: Snapshot) -> list[Diff]:
    """Boş liste = KAPI geçti (satır sayıları ve md5'ler birebir)."""
    diffs: list[Diff] = []
    for name in sorted(set(source.tables) | set(target.tables)):
        src = source.tables.get(name)
        dst = target.tables.get(name)
        if src is None:
            diffs.append(Diff(name, "extra_in_target", "-", str(dst.rows if dst else "?")))
            continue
        if dst is None:
            diffs.append(Diff(name, "missing_in_target", str(src.rows), "-"))
            continue
        if src.rows != dst.rows:
            diffs.append(Diff(name, "row_count", str(src.rows), str(dst.rows)))
            continue
        if src.md5 is not None and dst.md5 is not None and src.md5 != dst.md5:
            diffs.append(Diff(name, "md5", src.md5, dst.md5))
    return diffs


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def sha256_file(path: Path | str, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def build_manifest(
    *,
    dump_key: str,
    dump_size: int,
    dump_sha256: str,
    snapshot: Snapshot,
    pg_dump_version: str,
    server_version: str,
    schemas: Iterable[str],
) -> dict[str, Any]:
    return {
        "version": 1,
        "dump_key": dump_key,
        "dump_size": dump_size,
        "dump_sha256": dump_sha256,
        "pg_dump_version": pg_dump_version,
        "server_version": server_version,
        "schemas": list(schemas),
        "snapshot": snapshot.to_dict(),
    }

"""V2 §7.1 — yedek / geri yükleme çekirdeği (saf mantık) + cron entegrasyonu."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core import backup as bk


FULL_ENV = {
    "BACKUP_DATABASE_URL": "postgresql://postgres.abc:gizli-sifre@db.example.com:5432/postgres",
    "BACKUP_S3_ENDPOINT": "https://acc.r2.cloudflarestorage.com",
    "BACKUP_S3_BUCKET": "niyetsen-backups",
    "BACKUP_S3_ACCESS_KEY": "ak",
    "BACKUP_S3_SECRET_KEY": "sk",
}


# --- konfigürasyon ---------------------------------------------------------

def test_missing_lists_every_required_var_when_empty():
    missing = bk.BackupConfig.missing({})
    assert "BACKUP_DATABASE_URL (veya DIRECT_URL)" in missing
    assert "BACKUP_S3_BUCKET" in missing
    assert bk.BackupConfig.from_env({}) is None


def test_from_env_defaults_and_direct_url_fallback():
    env = dict(FULL_ENV)
    env.pop("BACKUP_DATABASE_URL")
    env["DIRECT_URL"] = "postgresql://u:p@h:5432/db"
    cfg = bk.BackupConfig.from_env(env)
    assert cfg is not None
    assert cfg.database_url == env["DIRECT_URL"]
    assert cfg.schemas == bk.DEFAULT_SCHEMAS
    assert cfg.retention_days == 30
    assert cfg.hour_utc == 1
    assert cfg.verify_md5 is True


def test_from_env_overrides_and_bad_ints_fall_back():
    env = {
        **FULL_ENV,
        "BACKUP_SCHEMAS": "public, auth ,",
        "BACKUP_RETENTION_DAYS": "abc",
        "BACKUP_HOUR_UTC": "27",
        "BACKUP_PREFIX": "/x/y/",
        "BACKUP_VERIFY_MD5": "false",
    }
    cfg = bk.BackupConfig.from_env(env)
    assert cfg is not None
    assert cfg.schemas == ("public", "auth")
    assert cfg.retention_days == 30
    assert cfg.hour_utc == 3  # 27 % 24
    assert cfg.prefix == "x/y"
    assert cfg.verify_md5 is False


# --- DSN / anahtar / zamanlama ---------------------------------------------

def test_mask_dsn_hides_password_only():
    masked = bk.mask_dsn(FULL_ENV["BACKUP_DATABASE_URL"])
    assert "gizli-sifre" not in masked
    assert masked.startswith("postgresql://postgres.abc:***@db.example.com")
    assert bk.mask_dsn("postgresql://host/db") == "postgresql://host/db"


def test_object_key_layout_is_utc_day_partitioned():
    ts = datetime(2026, 10, 17, 4, 5, 6, tzinfo=timezone(timedelta(hours=3)))  # 01:05:06 UTC
    key = bk.build_object_key("niyetsen/pg", ts)
    assert key == "niyetsen/pg/2026/10/17/niyetsen-20261017T010506Z.dump"
    assert bk.manifest_key(key) == key + ".manifest.json"
    assert bk.day_prefix("/niyetsen/pg/", ts) == "niyetsen/pg/2026/10/17/"


@pytest.mark.parametrize(
    ("hour", "already", "expected"),
    [(1, False, True), (2, False, False), (1, True, False), (25, False, True)],
)
def test_is_backup_due(hour, already, expected):
    now = datetime(2026, 10, 17, 1, 30, tzinfo=timezone.utc)
    assert bk.is_backup_due(now, hour, already) is expected


def test_select_expired_keys_respects_retention_and_naive_datetimes():
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    objects = [
        ("old.dump", now - timedelta(days=31)),
        ("edge.dump", now - timedelta(days=30)),  # tam sınır → kalır
        ("fresh.dump", now - timedelta(days=1)),
        ("naive-old.dump", (now - timedelta(days=40)).replace(tzinfo=None)),
    ]
    assert bk.select_expired_keys(objects, now, 30) == ["naive-old.dump", "old.dump"]
    assert bk.select_expired_keys(objects, now, 0) == []


# --- komutlar ----------------------------------------------------------------

def test_pg_dump_command_shape():
    cmd = bk.pg_dump_command("postgresql://u:p@h/db", ("public", "auth"), Path("/tmp/x.dump"))
    assert cmd[0] == "pg_dump"
    assert "--format=custom" in cmd and "--no-owner" in cmd and "--no-privileges" in cmd
    assert "--schema=public" in cmd and "--schema=auth" in cmd
    assert cmd[-1] == "--dbname=postgresql://u:p@h/db"
    assert "--file=/tmp/x.dump" in cmd


def test_pg_restore_command_and_identifier_guard():
    cmd = bk.pg_restore_command("postgresql://u@h/db", "/tmp/x.dump", jobs=0)
    assert cmd[:2] == ["pg_restore", "--no-owner"] and "--jobs=1" in cmd
    with pytest.raises(ValueError):
        bk.pg_dump_command("dsn", ("public; drop table users",), "/tmp/x")
    with pytest.raises(ValueError):
        bk.count_sql("public", 'users"; drop')


def test_prepare_target_sql_creates_supabase_roles_idempotently():
    sql = bk.prepare_target_sql()
    for role in ("anon", "authenticated", "service_role", "supabase_auth_admin"):
        assert f"rolname = '{role}'" in sql
        assert f"create role {role} nologin" in sql
    assert 'create extension if not exists "uuid-ossp"' in sql


# --- snapshot ----------------------------------------------------------------

def _fake_db(tables: dict[str, tuple[int, str]]):
    """`schema.table -> (rows, md5)` sahte psql."""

    def run_sql(sql: str) -> list[list[str]]:
        if sql.startswith("select table_name"):
            schema = sql.split("table_schema = '")[1].split("'")[0]
            return [[name.split(".", 1)[1]] for name in sorted(tables) if name.startswith(schema + ".")]
        for name, (rows, digest) in tables.items():
            schema, table = name.split(".", 1)
            if sql == bk.count_sql(schema, table):
                return [[str(rows)]]
            if sql == bk.md5_sql(schema, table):
                return [[digest]]
        raise AssertionError(f"beklenmeyen sql: {sql}")

    return run_sql


def test_take_snapshot_counts_and_md5_with_threshold():
    db = _fake_db({"public.users": (58, "aaa"), "public.tasks": (93, "bbb"), "auth.users": (58, "ccc")})
    snap = bk.take_snapshot(db, ("public", "auth"), md5_max_rows=60, now=datetime(2026, 10, 17, tzinfo=timezone.utc))
    assert snap.tables["public.users"] == bk.TableStat(rows=58, md5="aaa")
    assert snap.tables["public.tasks"] == bk.TableStat(rows=93, md5=None)  # eşik üstü → md5 atlandı
    assert snap.tables["auth.users"].md5 == "ccc"
    assert snap.total_rows == 58 + 93 + 58
    assert snap.taken_at.startswith("2026-10-17")


def test_snapshot_json_roundtrip_and_manifest_loading():
    snap = bk.take_snapshot(_fake_db({"public.users": (1, "x")}), ("public",))
    again = bk.Snapshot.from_dict(json.loads(snap.to_json()))
    assert again.tables == snap.tables and again.schemas == ["public"]
    manifest = bk.build_manifest(
        dump_key="k", dump_size=10, dump_sha256="s", snapshot=snap,
        pg_dump_version="pg_dump (PostgreSQL) 17.6", server_version="17.6", schemas=("public",),
    )
    assert manifest["version"] == 1 and manifest["snapshot"]["tables"]["public.users"]["rows"] == 1


def test_compare_snapshots_reports_each_kind_of_drift():
    src = bk.Snapshot("t0", ["public"], {
        "public.users": bk.TableStat(58, "a"),
        "public.tasks": bk.TableStat(93, "b"),
        "public.plans": bk.TableStat(59, "c"),
        "public.big": bk.TableStat(10, None),
        "public.only_src": bk.TableStat(1, "z"),
    })
    dst = bk.Snapshot("t1", ["public"], {
        "public.users": bk.TableStat(58, "a"),      # eşit
        "public.tasks": bk.TableStat(90, "b"),      # satır farkı
        "public.plans": bk.TableStat(59, "DIFF"),   # md5 farkı
        "public.big": bk.TableStat(10, "anything"),  # kaynakta md5 yok → yalnız satır
        "public.only_dst": bk.TableStat(2, "y"),
    })
    kinds = {(d.table, d.kind) for d in bk.compare_snapshots(src, dst)}
    assert kinds == {
        ("public.tasks", "row_count"),
        ("public.plans", "md5"),
        ("public.only_src", "missing_in_target"),
        ("public.only_dst", "extra_in_target"),
    }
    assert bk.compare_snapshots(src, src) == []


def test_sha256_file_matches_hashlib(tmp_path: Path):
    import hashlib

    f = tmp_path / "x.bin"
    payload = b"niyetsen" * 300_000  # >1 MiB → birden fazla parça okunur
    f.write_bytes(payload)
    assert bk.sha256_file(f) == hashlib.sha256(payload).hexdigest()


# --- cron entegrasyonu -------------------------------------------------------

def test_run_daily_not_configured_touches_nothing(monkeypatch: pytest.MonkeyPatch):
    from scripts import backup_io, backup_pg_dump

    monkeypatch.setattr(backup_io, "s3_client", lambda cfg: pytest.fail("S3 istemcisi açılmamalı"))
    result = backup_pg_dump.run_daily(env={})
    assert result["status"] == "not_configured"
    assert "BACKUP_S3_BUCKET" in result["missing"]


def test_run_daily_skips_outside_hour_and_when_already_taken(monkeypatch: pytest.MonkeyPatch):
    from scripts import backup_io, backup_pg_dump

    listed: list[str] = []

    class FakeClient:  # list_objects sahte sonuçları
        pass

    monkeypatch.setattr(backup_io, "s3_client", lambda cfg: FakeClient())
    monkeypatch.setattr(backup_io, "list_objects", lambda c, b, p: listed.append(p) or [])
    monkeypatch.setattr(backup_pg_dump, "perform_backup", lambda *a, **k: pytest.fail("yedek alınmamalı"))

    off_hour = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
    assert backup_pg_dump.run_daily(env=FULL_ENV, now=off_hour)["status"] == "skipped"
    assert listed == ["niyetsen/pg/2026/10/17/"]

    monkeypatch.setattr(backup_io, "list_objects", lambda c, b, p: [("x.dump", off_hour)])
    on_hour = datetime(2026, 10, 17, 1, 10, tzinfo=timezone.utc)
    result = backup_pg_dump.run_daily(env=FULL_ENV, now=on_hour)
    assert result == {"status": "skipped", "reason": "already_today"}


def test_run_daily_runs_backup_in_window_and_swallows_errors(monkeypatch: pytest.MonkeyPatch):
    from scripts import backup_io, backup_pg_dump

    monkeypatch.setattr(backup_io, "s3_client", lambda cfg: object())
    monkeypatch.setattr(backup_io, "list_objects", lambda c, b, p: [])
    on_hour = datetime(2026, 10, 17, 1, 10, tzinfo=timezone.utc)

    monkeypatch.setattr(backup_pg_dump, "perform_backup", lambda cfg, now=None: {"status": "done", "rows": 5})
    assert backup_pg_dump.run_daily(env=FULL_ENV, now=on_hour)["status"] == "done"

    def boom(cfg, now=None):
        raise backup_io.BackupToolError("pg_dump bulunamadı")

    monkeypatch.setattr(backup_pg_dump, "perform_backup", boom)
    result = backup_pg_dump.run_daily(env=FULL_ENV, now=on_hour)
    assert result["status"] == "error" and "pg_dump" in result["error"]
    # force → S3 listesi okunmadan doğrudan yedek
    monkeypatch.setattr(backup_io, "list_objects", lambda c, b, p: pytest.fail("force'ta listelenmez"))
    monkeypatch.setattr(backup_pg_dump, "perform_backup", lambda cfg, now=None: {"status": "done"})
    assert backup_pg_dump.run_daily(env=FULL_ENV, now=on_hour, force=True)["status"] == "done"


def test_cron_run_jobs_includes_backup_step_without_breaking(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_scheduled_jobs as cron_jobs
    from scripts import backup_pg_dump

    monkeypatch.setattr(
        "app.services.task_lifecycle_service.close_due_users",
        lambda repo, deadline_ts=None: {"results": [], "failed_users": 0},
    )
    monkeypatch.setattr(
        "app.services.notification_service.run_due_notifications",
        lambda repo, now_utc=None, deadline_ts=None: {"sent": 0},
    )
    seen = {"calls": 0}

    def fake_daily(**kwargs):
        seen["calls"] += 1
        return {"status": "error", "error": "kova yok"}

    monkeypatch.setattr(backup_pg_dump, "run_daily", fake_daily)
    monkeypatch.delenv("CRON_SKIP_BACKUP", raising=False)
    warnings = cron_jobs.run_jobs()
    assert seen["calls"] == 1
    assert any(w.startswith("backup: kova yok") for w in warnings)

    monkeypatch.setenv("CRON_SKIP_BACKUP", "true")
    seen["calls"] = 0
    assert not any("backup" in w for w in cron_jobs.run_jobs())
    assert seen["calls"] == 0

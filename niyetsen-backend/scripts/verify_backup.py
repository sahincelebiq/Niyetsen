"""Yedek doğrulama ve geri yükleme tatbikatı (V2 §7.1 madde 2, KAPI 0).

Alt komutlar:
  snapshot   --dsn URL [--schemas a,b] [--out snap.json]
             Bir veritabanının tablo başına satır sayısı + md5 anlık görüntüsü.
  compare    SOURCE.json TARGET.json
             İki anlık görüntüyü (ya da manifest + snapshot) karşılaştırır.
  fetch-latest [--out-dir DIR]
             S3'teki en yeni dump + manifest'i indirir (env ile yapılandırılır).
  drill      --dump FILE --manifest FILE --target-dsn URL [--no-prepare]
             Boş hedef Postgres'e pg_restore; hedefin snapshot'ını manifest'teki
             kaynak snapshot'la kıyaslar. Çıkış 0 = KAPI geçti.
  local-dump --dsn URL --out FILE [--schemas a,b]
             S3'süz yerel dump (+ yanına manifest) — tatbikatı kovasız koşmak için.

Haftalık tatbikat tek komut: `scripts/restore_drill_local.sh`
(initdb → drill → cluster kapat). Runbook: docs/GECIS_PROTOKOLU.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.backup import (  # noqa: E402
    DEFAULT_SCHEMAS,
    BackupConfig,
    Snapshot,
    build_manifest,
    compare_snapshots,
    mask_dsn,
    pg_dump_command,
    pg_restore_command,
    prepare_target_sql,
    sha256_file,
    take_snapshot,
)
from scripts import backup_io  # noqa: E402


def _schemas(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_SCHEMAS
    return tuple(s.strip() for s in raw.split(",") if s.strip()) or DEFAULT_SCHEMAS


def _load_snapshot(path: Path) -> Snapshot:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "snapshot" in data and "tables" not in data:  # manifest dosyası
        data = data["snapshot"]
    return Snapshot.from_dict(data)


def _print_report(source: Snapshot, target: Snapshot) -> int:
    diffs = compare_snapshots(source, target)
    print(f"kaynak: {len(source.tables)} tablo / {source.total_rows} satır ({source.taken_at})")
    print(f"hedef : {len(target.tables)} tablo / {target.total_rows} satır ({target.taken_at})")
    if not diffs:
        print("SONUÇ: EŞİT — satır sayıları ve md5'ler birebir. KAPI GEÇTİ ✅")
        return 0
    print(f"SONUÇ: {len(diffs)} fark — KAPI GEÇMEDİ ❌")
    for diff in diffs:
        print(f"  - {diff.table}: {diff.kind} (kaynak={diff.source}, hedef={diff.target})")
    return 1


# --------------------------------------------------------------------------

def cmd_snapshot(args: argparse.Namespace) -> int:
    schemas = _schemas(args.schemas)
    snap = take_snapshot(backup_io.psql_runner(args.dsn), schemas, verify_md5=not args.no_md5)
    text = snap.to_json()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"snapshot yazıldı: {args.out} ({len(snap.tables)} tablo, {snap.total_rows} satır)")
    else:
        print(text)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    return _print_report(_load_snapshot(Path(args.source)), _load_snapshot(Path(args.target)))


def cmd_fetch_latest(args: argparse.Namespace) -> int:
    env = backup_io.env_with_dotenv()
    cfg = BackupConfig.from_env(env)
    if cfg is None:
        print("S3 yapılandırması eksik: " + ", ".join(BackupConfig.missing(env)))
        return 2
    client = backup_io.s3_client(cfg)
    objects = backup_io.list_objects(client, cfg.s3_bucket, cfg.prefix.rstrip("/") + "/")
    dumps = sorted((o for o in objects if o[0].endswith(".dump")), key=lambda o: o[1])
    if not dumps:
        print("kovada dump yok")
        return 2
    dump_key = dumps[-1][0]
    out_dir = Path(args.out_dir)
    dump_path = out_dir / Path(dump_key).name
    manifest_path = out_dir / (Path(dump_key).name + ".manifest.json")
    backup_io.download_file(client, cfg.s3_bucket, dump_key, dump_path)
    backup_io.download_file(client, cfg.s3_bucket, dump_key + ".manifest.json", manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = sha256_file(dump_path)
    ok = actual == manifest.get("dump_sha256")
    print(f"indirildi: {dump_path} ({dump_path.stat().st_size} bayt) sha256 {'OK' if ok else 'UYUŞMUYOR'}")
    print(f"manifest : {manifest_path}")
    return 0 if ok else 1


def cmd_local_dump(args: argparse.Namespace) -> int:
    schemas = _schemas(args.schemas)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    backup_io.run_pg_dump(pg_dump_command(args.dsn, schemas, out), args.dsn)
    snap = take_snapshot(backup_io.psql_runner(args.dsn), schemas, now=now)
    manifest = build_manifest(
        dump_key=str(out),
        dump_size=out.stat().st_size,
        dump_sha256=sha256_file(out),
        snapshot=snap,
        pg_dump_version=backup_io.tool_version("pg_dump"),
        server_version=backup_io.server_version(args.dsn),
        schemas=schemas,
    )
    manifest_path = Path(str(out) + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"dump: {out} ({manifest['dump_size']} bayt, {len(snap.tables)} tablo, "
        f"{snap.total_rows} satır) kaynak={mask_dsn(args.dsn)}"
    )
    print(f"manifest: {manifest_path}")
    return 0


def cmd_drill(args: argparse.Namespace) -> int:
    dump = Path(args.dump)
    manifest_path = Path(args.manifest)
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_sha = manifest.get("dump_sha256")
    actual_sha = sha256_file(dump)
    if expected_sha and expected_sha != actual_sha:
        print(f"dump sha256 uyuşmuyor: manifest={expected_sha[:16]}… dosya={actual_sha[:16]}…")
        return 1
    print(f"dump bütünlüğü OK (sha256 {actual_sha[:16]}…) → hedef {mask_dsn(args.target_dsn)}")

    if not args.no_prepare:
        backup_io.run_psql_script(args.target_dsn, prepare_target_sql())
        print("hedef hazırlandı: Supabase rolleri (nologin) + uuid-ossp/pgcrypto")

    code, stderr = backup_io.run_pg_restore(pg_restore_command(args.target_dsn, dump, jobs=args.jobs), args.target_dsn)
    # PG15+ pg_dump `create schema public` yazar; hedefte zaten var → zararsız.
    benign = ('schema "public" already exists', "errors ignored on restore")
    error_lines = [
        ln for ln in stderr.splitlines() if "error" in ln.lower() and not any(b in ln for b in benign)
    ]
    print(f"pg_restore çıkış={code}, anlamlı hata satırı={len(error_lines)}")
    for line in error_lines[: args.show_errors]:
        print("  " + line[:200])

    source = Snapshot.from_dict(manifest["snapshot"])
    target = take_snapshot(
        backup_io.psql_runner(args.target_dsn),
        manifest.get("schemas") or source.schemas,
        verify_md5=all(stat.md5 is not None for stat in source.tables.values()),
    )
    if args.target_snapshot_out:
        Path(args.target_snapshot_out).write_text(target.to_json(), encoding="utf-8")
    return _print_report(source, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("snapshot")
    p.add_argument("--dsn", required=True)
    p.add_argument("--schemas")
    p.add_argument("--out")
    p.add_argument("--no-md5", action="store_true")
    p.set_defaults(fn=cmd_snapshot)

    p = sub.add_parser("compare")
    p.add_argument("source")
    p.add_argument("target")
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("fetch-latest")
    p.add_argument("--out-dir", default="/tmp/niyetsen-backup")
    p.set_defaults(fn=cmd_fetch_latest)

    p = sub.add_parser("local-dump")
    p.add_argument("--dsn", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--schemas")
    p.set_defaults(fn=cmd_local_dump)

    p = sub.add_parser("drill")
    p.add_argument("--dump", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--target-dsn", required=True)
    p.add_argument("--no-prepare", action="store_true")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--show-errors", type=int, default=10)
    p.add_argument("--target-snapshot-out")
    p.set_defaults(fn=cmd_drill)

    args = parser.parse_args(argv)
    try:
        return int(args.fn(args))
    except backup_io.BackupToolError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

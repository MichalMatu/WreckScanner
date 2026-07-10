from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config
from core.data_backup import snapshot_sqlite_database
from core.data_diagnostics import run_data_diagnostics
from core.zip_archive import (
    DEFAULT_ZIP_RESTORE_LIMITS,
    ZIP_READ_CHUNK_BYTES,
    ZipRestoreLimits,
    extract_verified_zip,
)

DEFAULT_DIAGNOSTICS_OUTPUT = config.DIAGNOSTICS_DIR / "data_diagnostics.json"
DEFAULT_ZIP_BACKUP_DIR = Path("kopie_zapasowe")
DEFAULT_RESTORE_SAFETY_DIR = DEFAULT_ZIP_BACKUP_DIR / "przed_odtworzeniem"
ZIP_SNAPSHOT_FORMAT = "wreckscanner-data-snapshot-v2"
ZIP_REQUIRED_PATHS = (
    config.DATABASE_PATH,
    config.FIELD_PHOTOS_DIR,
    config.PRIVATE_PHOTOS_DIR,
)
ZIP_OPTIONAL_PATHS = (DEFAULT_DIAGNOSTICS_OUTPUT,)
ZIP_SECRET_PATHS = (
    Path(".admin_password"),
    Path(".restic_password"),
)
ZIP_DATA_RESTORE_PATHS = (
    config.DATABASE_PATH,
    config.FIELD_PHOTOS_DIR,
    config.PRIVATE_PHOTOS_DIR,
    DEFAULT_DIAGNOSTICS_OUTPUT,
)


@dataclass(frozen=True)
class ZipBackupResult:
    status: str
    archive_path: Path | None
    diagnostics_status: str
    diagnostics_report: dict[str, Any]
    diagnostics_output: Path
    backup_paths: list[Path]
    manifest: dict[str, Any] | None
    message: str


@dataclass(frozen=True)
class ZipRestoreResult:
    status: str
    archive_path: Path
    safety_path: Path | None
    restored_paths: list[Path]
    message: str


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve(root_dir: Path, path: Path) -> Path:
    path = path.expanduser()
    return path if path.is_absolute() else root_dir / path


def _path_arg(root_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Ścieżka snapshotu musi znajdować się w katalogu aplikacji: {path}") from exc


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _validate_sqlite_database(database_path: Path) -> None:
    if not database_path.is_file():
        raise ValueError(f"Brak pliku bazy SQLite: {database_path}")
    connection = sqlite3.connect(database_path)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"SQLite integrity_check nie zwrócił ok: {result[0] if result else 'brak wyniku'}")
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        connection.close()

    required = {"schema_migrations", "field_photos", "settings", "privacy_requests"}
    missing = sorted(required - tables)
    if missing:
        raise ValueError(f"Baza SQLite nie ma wymaganych tabel: {', '.join(missing)}")


def _zip_add_directory(zip_file: zipfile.ZipFile, archive_name: str) -> None:
    name = archive_name.rstrip("/") + "/"
    info = zipfile.ZipInfo(name)
    info.external_attr = (stat.S_IFDIR | 0o700) << 16
    zip_file.writestr(info, b"")


def _zip_add_file(zip_file: zipfile.ZipFile, source_path: Path, archive_name: str) -> dict[str, Any]:
    if source_path.is_symlink():
        raise ValueError(f"Backup ZIP nie obsługuje symlinków: {source_path}")
    digest = hashlib.sha256()
    size_bytes = 0
    info = zipfile.ZipInfo(archive_name)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    with source_path.open("rb") as source, zip_file.open(info, "w", force_zip64=True) as destination:
        for chunk in iter(lambda: source.read(ZIP_READ_CHUNK_BYTES), b""):
            destination.write(chunk)
            digest.update(chunk)
            size_bytes += len(chunk)
    return {
        "path": archive_name,
        "type": "file",
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
    }


def _zip_add_path(
    zip_file: zipfile.ZipFile,
    *,
    root_dir: Path,
    source_path: Path,
    archive_name: str | None = None,
) -> list[dict[str, Any]]:
    if source_path.is_symlink():
        raise ValueError(f"Backup ZIP nie obsługuje symlinków: {source_path}")

    if archive_name is None:
        archive_name = _path_arg(root_dir, source_path)

    entries: list[dict[str, Any]] = []
    if source_path.is_dir():
        _zip_add_directory(zip_file, archive_name)
        entries.append({"path": archive_name.rstrip("/") + "/", "type": "directory"})
        for child in sorted(source_path.rglob("*")):
            child_archive_name = _path_arg(root_dir, child)
            if child.is_symlink():
                raise ValueError(f"Backup ZIP nie obsługuje symlinków: {child}")
            if child.is_dir():
                _zip_add_directory(zip_file, child_archive_name)
                entries.append({"path": child_archive_name.rstrip("/") + "/", "type": "directory"})
            elif child.is_file():
                entries.append(_zip_add_file(zip_file, child, child_archive_name))
        return entries

    if source_path.is_file():
        return [_zip_add_file(zip_file, source_path, archive_name)]

    raise ValueError(f"Ścieżka do backupu nie jest plikiem ani katalogiem: {source_path}")


def _collect_zip_paths(
    *,
    root_dir: Path,
    diagnostics_output: Path,
    include_secrets: bool,
) -> tuple[list[Path], list[Path]]:
    required = [_resolve(root_dir, path) for path in ZIP_REQUIRED_PATHS]
    missing_required = [path for path in required if not path.exists()]
    if missing_required:
        return [], missing_required

    optional_paths = list(ZIP_OPTIONAL_PATHS)
    if diagnostics_output != DEFAULT_DIAGNOSTICS_OUTPUT:
        optional_paths.append(diagnostics_output)
    if include_secrets:
        optional_paths.extend(ZIP_SECRET_PATHS)

    paths = [*required]
    paths.extend(_resolve(root_dir, path) for path in optional_paths if _resolve(root_dir, path).exists())
    return _dedupe(paths), []


def _zip_manifest(
    *,
    root_dir: Path,
    diagnostics_status: str,
    entries: list[dict[str, Any]],
    backup_paths: list[Path],
) -> dict[str, Any]:
    secret_paths = {_resolve(root_dir, path).resolve() for path in ZIP_SECRET_PATHS}
    secret_entries = [_path_arg(root_dir, path) for path in backup_paths if path.resolve() in secret_paths]
    return {
        "format": ZIP_SNAPSHOT_FORMAT,
        "created_at": _now_iso(),
        "diagnostics_status": diagnostics_status,
        "secrets_included": bool(secret_entries),
        "top_level_paths": [_path_arg(root_dir, path) for path in backup_paths],
        "entries": entries,
        "secret_entries": secret_entries,
    }


def create_zip_backup(
    *,
    root_dir: Path,
    output_dir: Path = DEFAULT_ZIP_BACKUP_DIR,
    output: Path | None = None,
    diagnostics_output: Path = DEFAULT_DIAGNOSTICS_OUTPUT,
    include_secrets: bool = False,
    strict: bool = False,
    check_images: bool = True,
) -> ZipBackupResult:
    root = root_dir.resolve()
    diagnostics_path = _resolve(root, diagnostics_output)
    _path_arg(root, diagnostics_path)
    report = run_data_diagnostics(
        field_photos_dir=_resolve(root, config.FIELD_PHOTOS_DIR),
        private_photos_dir=_resolve(root, config.PRIVATE_PHOTOS_DIR),
        check_images=check_images,
    )
    _json_write(diagnostics_path, report)

    issue_counts = report["summary"]["issues"]["by_severity"]
    if issue_counts["error"] > 0:
        return ZipBackupResult(
            status="blocked",
            archive_path=None,
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            manifest=None,
            message="Backup ZIP przerwany: diagnostyka danych ma błędy.",
        )
    if strict and (issue_counts["warning"] > 0 or issue_counts["info"] > 0):
        return ZipBackupResult(
            status="blocked",
            archive_path=None,
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            manifest=None,
            message="Backup ZIP przerwany: tryb strict blokuje ostrzeżenia diagnostyki.",
        )

    backup_paths, missing_required_paths = _collect_zip_paths(
        root_dir=root,
        diagnostics_output=diagnostics_output,
        include_secrets=include_secrets,
    )
    if missing_required_paths:
        return ZipBackupResult(
            status="blocked",
            archive_path=None,
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            manifest=None,
            message="Backup ZIP przerwany: brakuje wymaganych ścieżek: "
            + ", ".join(path.as_posix() for path in missing_required_paths),
        )

    output_path = output if output else output_dir / f"wreckscanner-snapshot-{_timestamp_for_filename()}.zip"
    output_path = _resolve(root, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or output_path.is_symlink():
        return ZipBackupResult(
            status="blocked",
            archive_path=output_path,
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=backup_paths,
            manifest=None,
            message=f"Backup ZIP przerwany: plik już istnieje: {output_path}",
        )

    temp_archive = output_path.with_name(f".{output_path.name}.tmp")
    if temp_archive.exists() or temp_archive.is_symlink():
        temp_archive.unlink()

    completed = False
    try:
        with tempfile.TemporaryDirectory(prefix="wreckscanner-zip-backup-") as tmp:
            temp_dir = Path(tmp)
            database_snapshot = snapshot_sqlite_database(
                _resolve(root, config.DATABASE_PATH),
                temp_dir / config.DATABASE_PATH,
            )
            _validate_sqlite_database(database_snapshot)
            entries: list[dict[str, Any]] = []
            temp_archive.touch(mode=0o600, exist_ok=False)
            with zipfile.ZipFile(temp_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
                entries.extend(
                    _zip_add_path(
                        zip_file,
                        root_dir=root,
                        source_path=database_snapshot,
                        archive_name=config.DATABASE_PATH.as_posix(),
                    )
                )
                for path in backup_paths:
                    if path.resolve() == _resolve(root, config.DATABASE_PATH).resolve():
                        continue
                    entries.extend(_zip_add_path(zip_file, root_dir=root, source_path=path))
                manifest = _zip_manifest(
                    root_dir=root,
                    diagnostics_status=str(report["status"]),
                    entries=entries,
                    backup_paths=backup_paths,
                )
                zip_file.writestr(
                    "manifest.json",
                    json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                )
        temp_archive.chmod(0o600)
        temp_archive.replace(output_path)
        output_path.chmod(0o600)
        completed = True
    finally:
        if not completed and temp_archive.exists():
            temp_archive.unlink()

    return ZipBackupResult(
        status="ok",
        archive_path=output_path,
        diagnostics_status=str(report["status"]),
        diagnostics_report=report,
        diagnostics_output=diagnostics_path,
        backup_paths=backup_paths,
        manifest=manifest,
        message="Backup ZIP zakończony.",
    )


def list_zip_backups(*, root_dir: Path, output_dir: Path = DEFAULT_ZIP_BACKUP_DIR) -> list[Path]:
    directory = _resolve(root_dir.resolve(), output_dir)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.zip"), key=lambda path: (path.stat().st_mtime, path.name), reverse=True)


def _restore_relative_paths(staging_dir: Path, *, restore_secrets: bool) -> list[Path]:
    paths: list[Path] = []
    candidates = list(ZIP_DATA_RESTORE_PATHS)
    if restore_secrets:
        candidates.extend(ZIP_SECRET_PATHS)
    for path in candidates:
        if (staging_dir / path).exists():
            paths.append(path)
    return paths


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _rollback_restore(
    root_dir: Path,
    safety_path: Path,
    *,
    moved_active_paths: list[Path],
    restored_paths: list[Path],
) -> None:
    for relative_path in reversed(restored_paths):
        active_path = root_dir / relative_path
        _remove_path(active_path)
    for relative_path in reversed(moved_active_paths):
        active_path = root_dir / relative_path
        _remove_path(active_path)
        backup_path = safety_path / relative_path
        if backup_path.exists() or backup_path.is_symlink():
            active_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(active_path))


def restore_zip_backup(
    *,
    root_dir: Path,
    archive_path: Path,
    safety_dir: Path = DEFAULT_RESTORE_SAFETY_DIR,
    restore_secrets: bool = False,
    limits: ZipRestoreLimits = DEFAULT_ZIP_RESTORE_LIMITS,
) -> ZipRestoreResult:
    root = root_dir.resolve()
    archive = _resolve(root, archive_path).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"Brak archiwum ZIP: {archive}")

    safety_root = _resolve(root, safety_dir)
    safety_path = safety_root / f"before-restore-{_timestamp_for_filename()}"
    restored_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="wreckscanner-zip-restore-") as tmp:
        staging_dir = Path(tmp)
        manifest = extract_verified_zip(
            archive,
            staging_dir,
            limits=limits,
            snapshot_format=ZIP_SNAPSHOT_FORMAT,
            secret_paths=ZIP_SECRET_PATHS,
        )
        _validate_sqlite_database(staging_dir / config.DATABASE_PATH)
        for required_path in (config.FIELD_PHOTOS_DIR, config.PRIVATE_PHOTOS_DIR):
            if not (staging_dir / required_path).is_dir():
                raise ValueError(f"Archiwum nie ma wymaganego katalogu: {required_path}")
        if restore_secrets and not manifest["secret_entries"]:
            raise ValueError("Zażądano odtworzenia sekretów, ale archiwum ich nie zawiera.")

        restore_paths = _restore_relative_paths(staging_dir, restore_secrets=restore_secrets)
        active_snapshot_paths = list(ZIP_DATA_RESTORE_PATHS)
        if restore_secrets:
            active_snapshot_paths.extend(ZIP_SECRET_PATHS)
        database_journal_paths = [
            config.DATABASE_PATH.with_name(f"{config.DATABASE_PATH.name}-wal"),
            config.DATABASE_PATH.with_name(f"{config.DATABASE_PATH.name}-shm"),
        ]
        moved_active_paths: list[Path] = []
        restored_relative_paths: list[Path] = []
        try:
            safety_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            safety_root.chmod(0o700)
            safety_path.mkdir(mode=0o700, exist_ok=False)
            for relative_path in [*active_snapshot_paths, *database_journal_paths]:
                active_path = root / relative_path
                if not active_path.exists() and not active_path.is_symlink():
                    continue
                backup_path = safety_path / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.move(str(active_path), str(backup_path))
                moved_active_paths.append(relative_path)

            for relative_path in restore_paths:
                source_path = staging_dir / relative_path
                target_path = root / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_path))
                restored_paths.append(target_path)
                restored_relative_paths.append(relative_path)
            if restore_secrets:
                for secret_path in ZIP_SECRET_PATHS:
                    restored_secret = root / secret_path
                    if restored_secret.is_file():
                        restored_secret.chmod(0o600)
            _validate_sqlite_database(root / config.DATABASE_PATH)
        except Exception:
            _rollback_restore(
                root,
                safety_path,
                moved_active_paths=moved_active_paths,
                restored_paths=restored_relative_paths,
            )
            raise

    return ZipRestoreResult(
        status="ok",
        archive_path=archive,
        safety_path=safety_path,
        restored_paths=restored_paths,
        message="Odtwarzanie ZIP zakończone.",
    )

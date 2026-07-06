from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config
from core.data_diagnostics import run_data_diagnostics

DEFAULT_DIAGNOSTICS_OUTPUT = config.DIAGNOSTICS_DIR / "data_diagnostics.json"
DEFAULT_ZIP_BACKUP_DIR = Path("kopie_zapasowe")
DEFAULT_RESTORE_SAFETY_DIR = DEFAULT_ZIP_BACKUP_DIR / "przed_odtworzeniem"
ZIP_SNAPSHOT_FORMAT = "wreckscanner-data-snapshot-v1"
ZIP_REQUIRED_PATHS = (
    config.DATABASE_PATH,
    config.FIELD_PHOTOS_DIR,
    config.PRIVATE_PHOTOS_DIR,
)
ZIP_OPTIONAL_PATHS = (
    config.PRIVACY_REQUESTS_DIR,
    Path(config.SETTINGS_FILENAME),
    DEFAULT_DIAGNOSTICS_OUTPUT,
)
ZIP_SECRET_PATHS = (
    Path(".admin_password"),
    Path(".restic_password"),
)
ZIP_RESTORE_PATHS = (
    config.DATABASE_PATH,
    config.FIELD_PHOTOS_DIR,
    config.PRIVATE_PHOTOS_DIR,
    config.PRIVACY_REQUESTS_DIR,
    Path(config.SETTINGS_FILENAME),
    DEFAULT_DIAGNOSTICS_OUTPUT,
    *ZIP_SECRET_PATHS,
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
    except ValueError:
        return path.as_posix()


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_relative_archive_path(name: str) -> Path:
    if not name or name.startswith("/") or "\\" in name:
        raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {name}")
    path = Path(name)
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {name}")
    return path


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


def _snapshot_sqlite_database(root_dir: Path, temp_dir: Path) -> Path:
    source_path = _resolve(root_dir, config.DATABASE_PATH)
    if not source_path.is_file():
        raise FileNotFoundError(f"Brak bazy danych: {source_path}")

    snapshot_path = temp_dir / config.DATABASE_PATH.name
    source = sqlite3.connect(source_path, timeout=30.0)
    try:
        target = sqlite3.connect(snapshot_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    _validate_sqlite_database(snapshot_path)
    return snapshot_path


def _zip_add_directory(zip_file: zipfile.ZipFile, archive_name: str) -> None:
    name = archive_name.rstrip("/") + "/"
    info = zipfile.ZipInfo(name)
    info.external_attr = 0o755 << 16
    zip_file.writestr(info, b"")


def _zip_add_file(zip_file: zipfile.ZipFile, source_path: Path, archive_name: str) -> dict[str, Any]:
    if source_path.is_symlink():
        raise ValueError(f"Backup ZIP nie obsługuje symlinków: {source_path}")
    stat = source_path.stat()
    zip_file.write(source_path, archive_name)
    return {
        "path": archive_name,
        "type": "file",
        "size_bytes": int(stat.st_size),
        "sha256": _sha256_file(source_path),
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
    include_secrets: bool,
) -> dict[str, Any]:
    secret_paths = {_resolve(root_dir, path).resolve() for path in ZIP_SECRET_PATHS}
    return {
        "format": ZIP_SNAPSHOT_FORMAT,
        "created_at": _now_iso(),
        "source_root": str(root_dir.resolve()),
        "diagnostics_status": diagnostics_status,
        "secrets_included": include_secrets,
        "top_level_paths": [_path_arg(root_dir, path) for path in backup_paths],
        "entries": entries,
        "secret_entries": [_path_arg(root_dir, path) for path in backup_paths if path.resolve() in secret_paths],
    }


def create_zip_backup(
    *,
    root_dir: Path,
    output_dir: Path = DEFAULT_ZIP_BACKUP_DIR,
    output: Path | None = None,
    diagnostics_output: Path = DEFAULT_DIAGNOSTICS_OUTPUT,
    include_secrets: bool = True,
    strict: bool = False,
    check_images: bool = True,
) -> ZipBackupResult:
    root = root_dir.resolve()
    diagnostics_path = _resolve(root, diagnostics_output)
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
    if output_path.exists():
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
    if temp_archive.exists():
        temp_archive.unlink()

    completed = False
    try:
        with tempfile.TemporaryDirectory(prefix="wreckscanner-zip-backup-") as tmp:
            temp_dir = Path(tmp)
            database_snapshot = _snapshot_sqlite_database(root, temp_dir)
            entries: list[dict[str, Any]] = []
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
                    include_secrets=include_secrets,
                )
                zip_file.writestr(
                    "manifest.json",
                    json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                )
        temp_archive.replace(output_path)
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


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> dict[str, Any]:
    with zipfile.ZipFile(archive_path) as zip_file:
        manifest_payload: dict[str, Any] | None = None
        for member in zip_file.infolist():
            relative_path = _require_relative_archive_path(member.filename.rstrip("/") or member.filename)
            destination = (target_dir / relative_path).resolve()
            try:
                destination.relative_to(target_dir.resolve())
            except ValueError as exc:
                raise ValueError(f"Nieprawidłowa ścieżka w archiwum: {member.filename}") from exc
            zip_file.extract(member, target_dir)
            if member.filename == "manifest.json":
                manifest_payload = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))

    if not manifest_payload:
        raise ValueError("Archiwum nie ma manifest.json.")
    if manifest_payload.get("format") != ZIP_SNAPSHOT_FORMAT:
        raise ValueError("Archiwum nie jest snapshotem danych WreckScanner.")
    return manifest_payload


def _restore_relative_paths(staging_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in ZIP_RESTORE_PATHS:
        if (staging_dir / path).exists():
            paths.append(path)
    return paths


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _rollback_restore(root_dir: Path, safety_path: Path, restore_paths: list[Path]) -> None:
    for relative_path in restore_paths:
        active_path = root_dir / relative_path
        _remove_path(active_path)
        backup_path = safety_path / relative_path
        if backup_path.exists():
            active_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(active_path))


def restore_zip_backup(
    *,
    root_dir: Path,
    archive_path: Path,
    safety_dir: Path = DEFAULT_RESTORE_SAFETY_DIR,
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
        _safe_extract_zip(archive, staging_dir)
        _validate_sqlite_database(staging_dir / config.DATABASE_PATH)
        for required_path in (config.FIELD_PHOTOS_DIR, config.PRIVATE_PHOTOS_DIR):
            if not (staging_dir / required_path).is_dir():
                raise ValueError(f"Archiwum nie ma wymaganego katalogu: {required_path}")

        restore_paths = _restore_relative_paths(staging_dir)
        active_snapshot_paths = list(ZIP_RESTORE_PATHS)
        database_journal_paths = [
            config.DATABASE_PATH.with_name(f"{config.DATABASE_PATH.name}-wal"),
            config.DATABASE_PATH.with_name(f"{config.DATABASE_PATH.name}-shm"),
        ]
        safety_path.mkdir(parents=True, exist_ok=False)
        for relative_path in [*active_snapshot_paths, *database_journal_paths]:
            active_path = root / relative_path
            if not active_path.exists() and not active_path.is_symlink():
                continue
            backup_path = safety_path / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(active_path), str(backup_path))

        try:
            for relative_path in restore_paths:
                source_path = staging_dir / relative_path
                target_path = root / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_path))
                restored_paths.append(target_path)
            _validate_sqlite_database(root / config.DATABASE_PATH)
        except Exception:
            _rollback_restore(root, safety_path, active_snapshot_paths)
            raise

    return ZipRestoreResult(
        status="ok",
        archive_path=archive,
        safety_path=safety_path,
        restored_paths=restored_paths,
        message="Odtwarzanie ZIP zakończone.",
    )

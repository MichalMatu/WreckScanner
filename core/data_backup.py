from __future__ import annotations

import json
import os
import sqlite3
import subprocess  # nosec B404
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core import config
from core.data_diagnostics import run_data_diagnostics

DEFAULT_DIAGNOSTICS_OUTPUT = config.DIAGNOSTICS_DIR / "data_diagnostics.json"
DEFAULT_RESTIC_TAGS = ("wreckscanner", "data")

Runner = Callable[..., subprocess.CompletedProcess[Any]]


@dataclass(frozen=True)
class ResticOptions:
    root_dir: Path
    restic_bin: str = "restic"
    repository: str | None = None
    password_file: Path | None = None


@dataclass(frozen=True)
class ResticCommandResult:
    command: list[str]
    returncode: int
    error: str | None = None


@dataclass(frozen=True)
class BackupRunResult:
    status: str
    diagnostics_status: str
    diagnostics_report: dict[str, Any]
    diagnostics_output: Path
    backup_paths: list[Path]
    message: str
    restic: ResticCommandResult | None = None


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _resolve(root_dir: Path, path: Path) -> Path:
    path = path.expanduser()
    return path if path.is_absolute() else root_dir / path


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


def snapshot_sqlite_database(source_path: Path, snapshot_path: Path) -> Path:
    """Create and validate a standalone SQLite snapshot using the Backup API."""
    if source_path.expanduser().is_symlink():
        raise ValueError(f"Baza danych nie może być symlinkiem: {source_path}")
    source_path = source_path.resolve()
    snapshot_path = snapshot_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Brak bazy danych: {source_path}")
    if snapshot_path.exists():
        raise FileExistsError(f"Plik snapshotu SQLite już istnieje: {snapshot_path}")

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    completed = False
    source = sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True, timeout=30.0)
    try:
        target = sqlite3.connect(snapshot_path)
        try:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                detail = integrity[0] if integrity else "brak wyniku"
                raise ValueError(f"SQLite integrity_check nie zwrócił ok: {detail}")
        finally:
            target.close()
        snapshot_path.chmod(0o600)
        completed = True
        return snapshot_path
    finally:
        source.close()
        if not completed:
            snapshot_path.unlink(missing_ok=True)


def _absolute_runtime_path(root_dir: Path, value: str | Path) -> str:
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else (root_dir / path).resolve())


def _restic_repository(root_dir: Path, value: str) -> str:
    if value.startswith("local:"):
        return f"local:{_absolute_runtime_path(root_dir, value.removeprefix('local:'))}"
    if ":" in value:
        return value
    return _absolute_runtime_path(root_dir, value)


def _restic_env(options: ResticOptions) -> dict[str, str]:
    env = os.environ.copy()
    root_dir = options.root_dir.resolve()
    if options.repository:
        env["RESTIC_REPOSITORY"] = _restic_repository(root_dir, options.repository)
    if options.password_file:
        env["RESTIC_PASSWORD_FILE"] = _absolute_runtime_path(root_dir, options.password_file)
    if env.get("RESTIC_REPOSITORY"):
        env["RESTIC_REPOSITORY"] = _restic_repository(root_dir, env["RESTIC_REPOSITORY"])
    if env.get("RESTIC_PASSWORD_FILE"):
        env["RESTIC_PASSWORD_FILE"] = _absolute_runtime_path(root_dir, env["RESTIC_PASSWORD_FILE"])
    if env.get("RESTIC_CACHE_DIR"):
        env["RESTIC_CACHE_DIR"] = _absolute_runtime_path(root_dir, env["RESTIC_CACHE_DIR"])
    else:
        env["RESTIC_CACHE_DIR"] = str(root_dir / ".cache" / "restic")
    if not env.get("RESTIC_REPOSITORY"):
        raise ValueError("Podaj --repo albo ustaw RESTIC_REPOSITORY.")
    if not env.get("RESTIC_PASSWORD") and not env.get("RESTIC_PASSWORD_FILE"):
        raise ValueError("Podaj --password-file albo ustaw RESTIC_PASSWORD_FILE/RESTIC_PASSWORD.")
    return env


def run_restic_command(
    args: list[str],
    options: ResticOptions,
    *,
    runner: Runner = subprocess.run,
    cwd: Path | None = None,
) -> ResticCommandResult:
    command = [options.restic_bin, *args]
    try:
        env = _restic_env(options)
        completed = runner(command, cwd=cwd or options.root_dir, env=env, check=False)
    except FileNotFoundError as exc:
        return ResticCommandResult(command=command, returncode=127, error=str(exc))
    except ValueError as exc:
        return ResticCommandResult(command=command, returncode=2, error=str(exc))
    return ResticCommandResult(command=command, returncode=int(completed.returncode))


def collect_backup_paths(
    *,
    root_dir: Path,
    diagnostics_output: Path,
    include_admin_password: bool = False,
    extra_paths: list[Path] | None = None,
) -> tuple[list[Path], list[Path]]:
    candidates = [
        _resolve(root_dir, config.FIELD_PHOTOS_DIR),
        _resolve(root_dir, config.PRIVATE_PHOTOS_DIR),
        _resolve(root_dir, diagnostics_output),
    ]
    if include_admin_password:
        candidates.append(root_dir / ".admin_password")
    missing: list[Path] = []
    for extra_path in extra_paths or []:
        resolved = _resolve(root_dir, extra_path)
        if not resolved.exists():
            missing.append(resolved)
        candidates.append(resolved)

    existing = [path for path in candidates if path.exists()]
    return _dedupe(existing), missing


def _restic_staging_path(staging_dir: Path, path: Path) -> str:
    return Path(os.path.relpath(path.resolve(), start=staging_dir.resolve())).as_posix()


def _forbidden_live_database_paths(root_dir: Path) -> tuple[Path, ...]:
    database_path = _resolve(root_dir, config.DATABASE_PATH).resolve()
    return (
        database_path,
        database_path.with_name(f"{database_path.name}-wal"),
        database_path.with_name(f"{database_path.name}-shm"),
    )


def _validate_extra_backup_paths(
    *,
    root_dir: Path,
    extra_paths: list[Path],
    include_admin_password: bool,
) -> None:
    admin_password = (root_dir / ".admin_password").resolve()
    restic_password = (root_dir / ".restic_password").resolve()
    forbidden = [*_forbidden_live_database_paths(root_dir), restic_password]
    if not include_admin_password:
        forbidden.append(admin_password)

    for raw_path in extra_paths:
        resolved = _resolve(root_dir, raw_path).resolve()
        if any(path == resolved or path.is_relative_to(resolved) for path in forbidden):
            raise ValueError(
                "Dodatkowa ścieżka nie może obejmować aktywnej bazy, plików WAL/SHM ani niejawnych sekretów."
            )


def run_backup(
    *,
    options: ResticOptions,
    diagnostics_output: Path = DEFAULT_DIAGNOSTICS_OUTPUT,
    include_admin_password: bool = False,
    extra_paths: list[Path] | None = None,
    strict: bool = False,
    check_images: bool = True,
    dry_run: bool = False,
    tags: tuple[str, ...] = DEFAULT_RESTIC_TAGS,
    runner: Runner = subprocess.run,
) -> BackupRunResult:
    root_dir = options.root_dir.resolve()
    diagnostics_path = _resolve(root_dir, diagnostics_output)
    report = run_data_diagnostics(
        field_photos_dir=_resolve(root_dir, config.FIELD_PHOTOS_DIR),
        private_photos_dir=_resolve(root_dir, config.PRIVATE_PHOTOS_DIR),
        check_images=check_images,
    )
    _json_write(diagnostics_path, report)

    issue_counts = report["summary"]["issues"]["by_severity"]
    if issue_counts["error"] > 0:
        return BackupRunResult(
            status="blocked",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            message="Backup przerwany: diagnostyka danych ma błędy.",
        )
    if strict and (issue_counts["warning"] > 0 or issue_counts["info"] > 0):
        return BackupRunResult(
            status="blocked",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            message="Backup przerwany: tryb strict blokuje ostrzeżenia diagnostyki.",
        )

    try:
        _validate_extra_backup_paths(
            root_dir=root_dir,
            extra_paths=extra_paths or [],
            include_admin_password=include_admin_password,
        )
        backup_paths, missing_extra_paths = collect_backup_paths(
            root_dir=root_dir,
            diagnostics_output=diagnostics_output,
            include_admin_password=include_admin_password,
            extra_paths=extra_paths,
        )
    except ValueError as exc:
        return BackupRunResult(
            status="blocked",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            message=str(exc),
        )
    if missing_extra_paths:
        return BackupRunResult(
            status="blocked",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=backup_paths,
            message="Backup przerwany: dodatkowa ścieżka nie istnieje.",
        )
    database_path = _resolve(root_dir, config.DATABASE_PATH).resolve()
    reported_backup_paths = [database_path, *backup_paths]
    if not backup_paths and not database_path.is_file():
        return BackupRunResult(
            status="blocked",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=[],
            message="Backup przerwany: brak istniejących ścieżek do backupu.",
        )

    try:
        with tempfile.TemporaryDirectory(prefix=".restic-backup-staging-", dir=root_dir) as tmp:
            staging_dir = Path(tmp)
            database_snapshot = snapshot_sqlite_database(
                database_path,
                staging_dir / config.DATABASE_PATH,
            )
            staged_sources = [database_snapshot, *backup_paths]
            args = ["backup", "--group-by", "host,tags"]
            if dry_run:
                args.append("--dry-run")
            for tag in tags:
                args.extend(["--tag", tag])
            args.extend(_restic_staging_path(staging_dir, path) for path in staged_sources)
            restic_result = run_restic_command(args, options, runner=runner, cwd=staging_dir)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return BackupRunResult(
            status="failed",
            diagnostics_status=str(report["status"]),
            diagnostics_report=report,
            diagnostics_output=diagnostics_path,
            backup_paths=reported_backup_paths,
            message=f"Nie udało się utworzyć spójnego snapshotu SQLite: {exc}",
        )

    status = "ok" if restic_result.returncode == 0 else "failed"
    message = "Backup zakończony." if status == "ok" else "Backup nie powiódł się."
    if restic_result.error:
        message = restic_result.error
    return BackupRunResult(
        status=status,
        diagnostics_status=str(report["status"]),
        diagnostics_report=report,
        diagnostics_output=diagnostics_path,
        backup_paths=reported_backup_paths,
        message=message,
        restic=restic_result,
    )


def restic_init(options: ResticOptions, *, runner: Runner = subprocess.run) -> ResticCommandResult:
    return run_restic_command(["init"], options, runner=runner)


def restic_check(options: ResticOptions, *, runner: Runner = subprocess.run) -> ResticCommandResult:
    return run_restic_command(["check"], options, runner=runner)


def restic_snapshots(options: ResticOptions, *, runner: Runner = subprocess.run) -> ResticCommandResult:
    return run_restic_command(["snapshots"], options, runner=runner)


def restic_forget(
    options: ResticOptions,
    *,
    keep_daily: int,
    keep_weekly: int,
    keep_monthly: int,
    prune: bool,
    runner: Runner = subprocess.run,
) -> ResticCommandResult:
    args = [
        "forget",
        "--keep-daily",
        str(keep_daily),
        "--keep-weekly",
        str(keep_weekly),
        "--keep-monthly",
        str(keep_monthly),
    ]
    if prune:
        args.append("--prune")
    return run_restic_command(args, options, runner=runner)

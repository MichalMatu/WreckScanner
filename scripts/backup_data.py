#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from core.data_backup import (  # noqa: E402
    DEFAULT_DIAGNOSTICS_OUTPUT,
    ResticCommandResult,
    ResticOptions,
    restic_check,
    restic_forget,
    restic_init,
    restic_snapshots,
    run_backup,
)
from core.data_diagnostics import format_data_diagnostics  # noqa: E402
from core.zip_backup import (  # noqa: E402
    DEFAULT_ZIP_BACKUP_DIR,
    create_zip_backup,
    list_zip_backups,
    restore_zip_backup,
)


def _root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root-dir", type=Path, default=ROOT_DIR, help="Katalog projektu WreckScanner.")
    return parser


def _common_parser() -> argparse.ArgumentParser:
    parser = _root_parser()
    parser.add_argument("--repo", help="Repozytorium restic. Alternatywnie ustaw RESTIC_REPOSITORY.")
    parser.add_argument(
        "--password-file", type=Path, help="Plik hasła restic. Alternatywnie ustaw RESTIC_PASSWORD_FILE."
    )
    parser.add_argument("--restic-bin", default="restic", help="Ścieżka do binarki restic.")
    return parser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup lokalnej bazy WreckScanner przez restic.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    root_common = _root_parser()
    common = _common_parser()

    subparsers.add_parser("init", parents=[common], help="Zainicjuj repozytorium restic.")
    subparsers.add_parser("check", parents=[common], help="Sprawdź repozytorium restic.")
    subparsers.add_parser("snapshots", parents=[common], help="Pokaż snapshoty restic.")

    run_parser = subparsers.add_parser("run", parents=[common], help="Wykonaj diagnostykę i backup danych.")
    run_parser.add_argument("--diagnostics-output", type=Path, default=DEFAULT_DIAGNOSTICS_OUTPUT)
    run_parser.add_argument(
        "--include-admin-password", action="store_true", help="Dołącz lokalny plik .admin_password."
    )
    run_parser.add_argument(
        "--include-path", type=Path, action="append", default=[], help="Dodatkowa ścieżka do backupu."
    )
    run_parser.add_argument("--no-image-check", action="store_true", help="Nie otwieraj obrazów podczas diagnostyki.")
    run_parser.add_argument(
        "--strict", action="store_true", help="Przerwij backup także przy ostrzeżeniach diagnostyki."
    )
    run_parser.add_argument("--dry-run", action="store_true", help="Przekaż --dry-run do restic backup.")

    forget_parser = subparsers.add_parser("forget", parents=[common], help="Zastosuj retencję snapshotów.")
    forget_parser.add_argument("--keep-daily", type=int, default=14)
    forget_parser.add_argument("--keep-weekly", type=int, default=8)
    forget_parser.add_argument("--keep-monthly", type=int, default=6)
    forget_parser.add_argument("--prune", action="store_true", help="Po retencji zwolnij nieużywane dane repozytorium.")

    zip_parser = subparsers.add_parser(
        "zip", parents=[root_common], help="Utwórz pełny snapshot danych aplikacji w ZIP."
    )
    zip_parser.add_argument("--output-dir", type=Path, default=DEFAULT_ZIP_BACKUP_DIR)
    zip_parser.add_argument("--output", type=Path, help="Dokładna ścieżka pliku ZIP do utworzenia.")
    zip_parser.add_argument("--diagnostics-output", type=Path, default=DEFAULT_DIAGNOSTICS_OUTPUT)
    zip_parser.add_argument(
        "--include-secrets",
        action="store_true",
        help="Jawnie dołącz .admin_password i .restic_password do niezaszyfrowanego ZIP.",
    )
    zip_parser.add_argument("--no-image-check", action="store_true", help="Nie otwieraj obrazów podczas diagnostyki.")
    zip_parser.add_argument(
        "--strict", action="store_true", help="Przerwij backup także przy ostrzeżeniach diagnostyki."
    )

    restore_parser = subparsers.add_parser("restore-zip", parents=[root_common], help="Odtwórz dane z ZIP snapshotu.")
    restore_parser.add_argument("--archive", type=Path, required=True, help="Ścieżka do archiwum ZIP.")
    restore_parser.add_argument(
        "--restore-secrets",
        action="store_true",
        help="Jawnie odtwórz .admin_password i .restic_password zawarte w ZIP.",
    )

    list_parser = subparsers.add_parser("list-zips", parents=[root_common], help="Pokaż lokalne snapshoty ZIP.")
    list_parser.add_argument("--output-dir", type=Path, default=DEFAULT_ZIP_BACKUP_DIR)

    return parser.parse_args()


def _options(args: argparse.Namespace) -> ResticOptions:
    return ResticOptions(
        root_dir=args.root_dir.resolve(),
        restic_bin=args.restic_bin,
        repository=args.repo,
        password_file=args.password_file,
    )


def _print_restic_result(result: ResticCommandResult) -> int:
    if result.error:
        print(result.error, file=sys.stderr)
    return result.returncode


def _run_backup(args: argparse.Namespace) -> int:
    options = _options(args)
    result = run_backup(
        options=options,
        diagnostics_output=args.diagnostics_output,
        include_admin_password=args.include_admin_password,
        extra_paths=args.include_path,
        strict=args.strict,
        check_images=not args.no_image_check,
        dry_run=args.dry_run,
    )

    print(format_data_diagnostics(result.diagnostics_report))
    print("")
    print(f"Diagnostyka zapisana: {result.diagnostics_output}")
    if result.backup_paths:
        print("Ścieżki backupu:")
        for path in result.backup_paths:
            print(f"- {path}")
    print(result.message)
    if result.restic:
        print("Polecenie restic:")
        print(" ".join(result.restic.command))
        return result.restic.returncode
    return 0 if result.status == "ok" else 1


def _run_zip_backup(args: argparse.Namespace) -> int:
    result = create_zip_backup(
        root_dir=args.root_dir,
        output_dir=args.output_dir,
        output=args.output,
        diagnostics_output=args.diagnostics_output,
        include_secrets=args.include_secrets,
        strict=args.strict,
        check_images=not args.no_image_check,
    )

    print(format_data_diagnostics(result.diagnostics_report))
    print("")
    print(f"Diagnostyka zapisana: {result.diagnostics_output}")
    if result.backup_paths:
        print("Ścieżki snapshotu:")
        for path in result.backup_paths:
            print(f"- {path}")
    print(result.message)
    if result.archive_path:
        print(f"Archiwum ZIP: {result.archive_path}")
    if result.manifest:
        print(f"Liczba wpisów w archiwum: {len(result.manifest['entries'])}")
    return 0 if result.status == "ok" else 1


def _run_zip_restore(args: argparse.Namespace) -> int:
    result = restore_zip_backup(
        root_dir=args.root_dir,
        archive_path=args.archive,
        restore_secrets=args.restore_secrets,
    )
    print(result.message)
    print(f"Archiwum ZIP: {result.archive_path}")
    if result.safety_path:
        print(f"Kopia stanu sprzed odtwarzania: {result.safety_path}")
    print("Odtworzone ścieżki:")
    for path in result.restored_paths:
        print(f"- {path}")
    return 0 if result.status == "ok" else 1


def _list_zip_backups(args: argparse.Namespace) -> int:
    backups = list_zip_backups(root_dir=args.root_dir, output_dir=args.output_dir)
    if not backups:
        print("Brak lokalnych snapshotów ZIP.")
        return 0
    for path in backups:
        size_mib = path.stat().st_size / (1024 * 1024)
        print(f"{path}\t{size_mib:.1f} MiB")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "init":
        return _print_restic_result(restic_init(_options(args)))
    if args.command == "check":
        return _print_restic_result(restic_check(_options(args)))
    if args.command == "snapshots":
        return _print_restic_result(restic_snapshots(_options(args)))
    if args.command == "forget":
        return _print_restic_result(
            restic_forget(
                _options(args),
                keep_daily=args.keep_daily,
                keep_weekly=args.keep_weekly,
                keep_monthly=args.keep_monthly,
                prune=args.prune,
            )
        )
    if args.command == "run":
        return _run_backup(args)
    if args.command == "zip":
        return _run_zip_backup(args)
    if args.command == "restore-zip":
        return _run_zip_restore(args)
    if args.command == "list-zips":
        return _list_zip_backups(args)
    raise AssertionError(f"Nieznana komenda: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

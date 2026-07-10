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

from core import config  # noqa: E402
from core.database import migrate_json_to_database, validate_runtime_database  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Waliduj aktywna baze SQLite albo jawnie zaimportuj historyczne JSON-y WreckScanner."
    )
    parser.add_argument("--root-dir", type=Path, default=ROOT_DIR)
    parser.add_argument("--database", type=Path, default=config.DATABASE_PATH)
    parser.add_argument(
        "--skip-backup-check",
        action="store_true",
        help="Pomin wymog istniejacego snapshotu restic. Tylko dla testow lub restore dry-run.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--validate-only",
        action="store_true",
        help="Sprawdz integralnosc aktywnej SQLite, migracje i odwolania do plikow; legacy JSON jest ignorowany.",
    )
    mode.add_argument(
        "--migrate-legacy-json",
        action="store_true",
        help="Jawnie zaimportuj historyczne record.json, settings.json i zgloszenia_prywatnosci do SQLite.",
    )
    args = parser.parse_args(argv)
    if args.skip_backup_check and not args.migrate_legacy_json:
        parser.error("--skip-backup-check jest dozwolone tylko z --migrate-legacy-json")
    return args


def _print_runtime_validation(args: argparse.Namespace) -> None:
    validation = validate_runtime_database(root_dir=args.root_dir, database_path=args.database)
    print(f"Baza danych: {validation.database_path}")
    print(f"SQLite quick_check: {', '.join(validation.quick_check)}")
    print(f"Naruszenia kluczy obcych: {len(validation.foreign_key_violations)}")
    print(f"Migracje: {len(validation.applied_migrations)}/{len(validation.expected_migrations)}")
    print(f"Zdjecia terenowe: {validation.field_photos}")
    print(f"Ustawienia: {validation.settings}")
    print(f"Zgloszenia prywatnosci: {validation.privacy_requests}")
    print(f"Brakujace sciezki: {len(validation.missing_paths)}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.validate_only:
            _print_runtime_validation(args)
            print("Walidacja aktywnej SQLite zakonczona.")
            return 0

        report = migrate_json_to_database(
            root_dir=args.root_dir,
            database_path=args.database,
            require_backup=not args.skip_backup_check,
        )
        print(f"Zdjecia terenowe legacy: {report.migrated_field_photos}/{report.field_photo_records}")
        print(f"Ustawienia legacy: {report.migrated_settings}/{report.settings_records}")
        print(f"Zgloszenia prywatnosci legacy: {report.migrated_privacy_requests}/{report.privacy_request_records}")
        _print_runtime_validation(args)
        print("Jawna migracja legacy JSON -> SQLite zakonczona.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Blad: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

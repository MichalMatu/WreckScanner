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
from core.database import migrate_json_to_database, validate_database_against_json  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migruj lokalne JSON-y WreckScanner do SQLite.")
    parser.add_argument("--root-dir", type=Path, default=ROOT_DIR)
    parser.add_argument("--database", type=Path, default=config.DATABASE_PATH)
    parser.add_argument(
        "--skip-backup-check",
        action="store_true",
        help="Pomin wymog istniejacego snapshotu restic. Tylko dla testow lub restore dry-run.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Nie migruj danych, tylko sprawdz zgodnosc DB z JSON i sciezkami plikow.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.validate_only:
        validation = validate_database_against_json(root_dir=args.root_dir, database_path=args.database)
        print(f"Zdjecia terenowe DB/JSON: {validation.database_field_photos}/{validation.field_photo_records}")
        print(f"Ustawienia DB/JSON: {validation.database_settings}/{validation.settings_records}")
        print(
            "Zgloszenia prywatnosci DB/JSON: "
            f"{validation.database_privacy_requests}/{validation.privacy_request_records}"
        )
        print(f"Brakujace sciezki: {len(validation.missing_paths)}")
        print("Walidacja DB zakonczona.")
        return 0

    report = migrate_json_to_database(
        root_dir=args.root_dir,
        database_path=args.database,
        require_backup=not args.skip_backup_check,
    )
    validation = validate_database_against_json(root_dir=args.root_dir, database_path=args.database)
    print(f"Baza danych: {report.database_path}")
    print(f"Zdjecia terenowe: {report.migrated_field_photos}/{report.field_photo_records}")
    print(f"Ustawienia: {report.migrated_settings}/{report.settings_records}")
    print(f"Zgloszenia prywatnosci: {report.migrated_privacy_requests}/{report.privacy_request_records}")
    print(f"Brakujace sciezki: {len(validation.missing_paths)}")
    print("Migracja JSON -> DB zakonczona.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

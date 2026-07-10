import io
import json
import sqlite3
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from core.database import (
    migrate_json_to_database,
    validate_legacy_json_migration,
    validate_runtime_database,
)
from scripts import migrate_json_to_db

ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATION_COUNT = len(list((ROOT_DIR / "database" / "migrations").glob("*.sql")))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def write_bytes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")


def field_photo_record(photo_id: str = "photo_20260704T080000Z_test") -> dict:
    return {
        "id": photo_id,
        "created_at": "2026-07-04T08:00:00Z",
        "submitted_at": "2026-07-04T08:01:00Z",
        "captured_at": "2026-07-04T07:59:00",
        "issue_type": "vehicle",
        "vehicle_insurance_status": "uninsured",
        "vehicle_insurance_checked_at": "2026-07-04T08:05:00Z",
        "vehicle_resolution_status": "removed",
        "vehicle_resolution_updated_at": "2026-07-04T08:06:00Z",
        "lat": 51.1,
        "lon": 17.03,
        "coordinate_source": "map",
        "position_updated_at": "2026-07-04T08:02:00Z",
        "public_review_status": "approved",
        "reviewed_at": "2026-07-04T08:03:00Z",
        "owner_redactions_updated_at": "2026-07-04T08:04:00Z",
        "redactions": [{"points": [{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.4}]}],
        "exif": {"make": "camera"},
        "original_filename": "photo.jpg",
        "content_type": "image/jpeg",
        "format": "JPEG",
        "size_bytes": 4,
        "image_width": 10,
        "image_height": 8,
        "private_original_file": f"field_photos/{photo_id}/original.jpg",
        "public_image_file": "public.jpg",
        "public_thumb_file": "public_thumb.jpg",
        "public_width": 10,
        "public_height": 8,
        "submission_owner": "public:test",
        "edit_token_salt": "salt",
        "edit_token_hash": "hash",
        "edit_token_created_at": "2026-07-04T08:00:00Z",
        "links": {"geoportal": "https://example.test/map"},
    }


def write_backup_marker(root: Path) -> None:
    marker = root / ".backups" / "wreckscanner-restic" / "snapshots" / "snapshot"
    write_bytes(marker)


def seed_root(root: Path) -> dict:
    record = field_photo_record()
    photo_dir = root / "zdjecia_terenowe" / record["id"]
    write_json(photo_dir / "record.json", record)
    write_bytes(root / "prywatne_zdjecia" / record["private_original_file"])
    write_bytes(photo_dir / "public.jpg")
    write_bytes(photo_dir / "public_thumb.jpg")
    write_json(
        root / "settings.json", {"public_layers": {"vehicles": True}, "public_features": {"photo_uploads": True}}
    )
    write_json(
        root / "zgloszenia_prywatnosci" / "privacy_20260704T080000Z_test.json",
        {
            "id": "privacy_20260704T080000Z_test",
            "created_at": "2026-07-04T08:00:00Z",
            "updated_at": "2026-07-04T08:00:00Z",
            "status": "new",
            "email": "person@example.test",
            "target": "photo_20260704T080000Z_test",
            "reason": "remove",
            "handled_at": None,
            "admin_note": "",
        },
    )
    write_backup_marker(root)
    return record


class JsonToDatabaseMigrationTests(unittest.TestCase):
    def test_migrates_json_state_to_sqlite_without_touching_photo_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = seed_root(root)
            private_path = root / "prywatne_zdjecia" / record["private_original_file"]
            before_private = private_path.read_bytes()

            report = migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            second_report = migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

            self.assertEqual(report.migrated_field_photos, 1)
            self.assertEqual(second_report.migrated_field_photos, 1)
            self.assertEqual(private_path.read_bytes(), before_private)

            connection = sqlite3.connect(root / "wreckscanner.sqlite3")
            self.addCleanup(connection.close)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM field_photos").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM privacy_requests").fetchone()[0], 1)
            row = connection.execute(
                "SELECT id, issue_type, vehicle_insurance_status, vehicle_insurance_checked_at, vehicle_resolution_status, vehicle_resolution_updated_at, private_original_file, edit_token_hash, exif_json FROM field_photos"
            ).fetchone()
            self.assertEqual(row[0], record["id"])
            self.assertEqual(row[1], "vehicle")
            self.assertEqual(row[2], "uninsured")
            self.assertEqual(row[3], "2026-07-04T08:05:00Z")
            self.assertEqual(row[4], "removed")
            self.assertEqual(row[5], "2026-07-04T08:06:00Z")
            self.assertEqual(row[6], record["private_original_file"])
            self.assertEqual(row[7], "hash")
            self.assertEqual(json.loads(row[8]), {"make": "camera"})
            validation = validate_legacy_json_migration(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            self.assertEqual(validation.database_field_photos, 1)
            self.assertEqual(validation.field_photo_records, 1)
            self.assertEqual(validation.missing_paths, [])

    def test_runtime_validation_uses_sqlite_without_comparing_legacy_json(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = seed_root(root)
            migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            (root / "zdjecia_terenowe" / record["id"] / "record.json").unlink()
            (root / "settings.json").unlink()
            for path in (root / "zgloszenia_prywatnosci").glob("*.json"):
                path.unlink()

            report = validate_runtime_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

            self.assertEqual(report.quick_check, ["ok"])
            self.assertEqual(report.foreign_key_violations, [])
            self.assertEqual(report.missing_migrations, [])
            self.assertEqual(report.unexpected_migrations, [])
            self.assertEqual(report.field_photos, 1)
            self.assertEqual(report.settings, 2)
            self.assertEqual(report.privacy_requests, 1)
            self.assertEqual(report.missing_paths, [])

    def test_validate_only_cli_ignores_legacy_json_counts(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = seed_root(root)
            migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            (root / "zdjecia_terenowe" / record["id"] / "record.json").unlink()
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = migrate_json_to_db.main(
                    ["--root-dir", str(root), "--database", "wreckscanner.sqlite3", "--validate-only"]
                )

            self.assertEqual(exit_code, 0, stderr.getvalue())
            self.assertIn("SQLite quick_check: ok", stdout.getvalue())
            self.assertIn(f"Migracje: {MIGRATION_COUNT}/{MIGRATION_COUNT}", stdout.getvalue())
            self.assertNotIn("DB/JSON", stdout.getvalue())

    def test_legacy_cli_migration_requires_and_accepts_explicit_mode(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_root(root)
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stderr(stderr), self.assertRaises(SystemExit) as missing_mode:
                migrate_json_to_db.parse_args(["--root-dir", str(root), "--database", "wreckscanner.sqlite3"])
            self.assertEqual(missing_mode.exception.code, 2)
            stderr.seek(0)
            stderr.truncate()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = migrate_json_to_db.main(
                    ["--root-dir", str(root), "--database", "wreckscanner.sqlite3", "--migrate-legacy-json"]
                )

            self.assertEqual(exit_code, 0, stderr.getvalue())
            self.assertIn("Jawna migracja legacy JSON -> SQLite zakonczona.", stdout.getvalue())
            self.assertTrue((root / "wreckscanner.sqlite3").is_file())

    def test_runtime_validation_blocks_missing_applied_migration(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_root(root)
            migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            connection = sqlite3.connect(root / "wreckscanner.sqlite3")
            try:
                connection.execute("DELETE FROM schema_migrations WHERE version = '005_field_photo_vehicle_resolution'")
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(ValueError, "missing_migrations=005_field_photo_vehicle_resolution"):
                validate_runtime_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

    def test_runtime_validation_blocks_foreign_key_violations(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_root(root)
            migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            connection = sqlite3.connect(root / "wreckscanner.sqlite3")
            try:
                connection.executescript(
                    """
                    PRAGMA foreign_keys = OFF;
                    CREATE TABLE validation_parent (id INTEGER PRIMARY KEY);
                    CREATE TABLE validation_child (
                        id INTEGER PRIMARY KEY,
                        parent_id INTEGER REFERENCES validation_parent(id)
                    );
                    INSERT INTO validation_child (id, parent_id) VALUES (1, 999);
                    """
                )
                connection.commit()
            finally:
                connection.close()

            with self.assertRaisesRegex(ValueError, "foreign_key_violations=1"):
                validate_runtime_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

    def test_runtime_validation_blocks_missing_referenced_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = seed_root(root)
            migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            (root / "zdjecia_terenowe" / record["id"] / "public_thumb.jpg").unlink()

            with self.assertRaisesRegex(ValueError, "missing_paths=1"):
                validate_runtime_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

    def test_runtime_validation_does_not_create_a_missing_database(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "wreckscanner.sqlite3"

            with self.assertRaisesRegex(ValueError, "Brak aktywnej bazy SQLite"):
                validate_runtime_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

            self.assertFalse(database.exists())

    def test_migration_requires_backup_snapshot_by_default(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_root(root)
            for path in (root / ".backups" / "wreckscanner-restic" / "snapshots").glob("*"):
                path.unlink()

            with self.assertRaisesRegex(ValueError, "backup restic"):
                migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))

    def test_migration_blocks_missing_photo_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = seed_root(root)
            (root / "prywatne_zdjecia" / record["private_original_file"]).unlink()

            with self.assertRaisesRegex(ValueError, "Brak prywatnego oryginalu"):
                migrate_json_to_database(root_dir=root, database_path=Path("wreckscanner.sqlite3"))


if __name__ == "__main__":
    unittest.main()

import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.database import migrate_json_to_database, validate_database_against_json


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
                "SELECT id, issue_type, private_original_file, edit_token_hash, exif_json FROM field_photos"
            ).fetchone()
            self.assertEqual(row[0], record["id"])
            self.assertEqual(row[1], "vehicle")
            self.assertEqual(row[2], record["private_original_file"])
            self.assertEqual(row[3], "hash")
            self.assertEqual(json.loads(row[4]), {"make": "camera"})
            validation = validate_database_against_json(root_dir=root, database_path=Path("wreckscanner.sqlite3"))
            self.assertEqual(validation.database_field_photos, 1)
            self.assertEqual(validation.field_photo_records, 1)
            self.assertEqual(validation.missing_paths, [])

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

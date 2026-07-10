import json
import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from core.database import migrate_json_to_database
from core.photo_retention import retire_private_originals

NOW = datetime(2026, 6, 5, 12, 0, 0, tzinfo=timezone.utc)
OLD_REVIEWED_AT = "2025-12-01T10:00:00Z"
RECENT_REVIEWED_AT = "2026-05-01T10:00:00Z"


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_jpeg(path: Path, size=(48, 32), color=(70, 120, 160)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, "JPEG", quality=90)


def field_record(photo_id: str, *, status: str = "approved", reviewed_at: str = OLD_REVIEWED_AT):
    return {
        "id": photo_id,
        "created_at": "2025-11-01T10:00:00Z",
        "original_filename": "teren.jpg",
        "content_type": "image/jpeg",
        "format": "JPEG",
        "size_bytes": 100,
        "image_width": 48,
        "image_height": 32,
        "issue_type": "vehicle",
        "lat": 51.1,
        "lon": 17.2,
        "coordinate_source": "map",
        "private_original_file": f"field_photos/{photo_id}/original.jpg",
        "public_review_status": status,
        "redactions": [],
        "reviewed_at": reviewed_at,
        "links": {},
    }


def db_record(root: Path, photo_id: str) -> dict:
    connection = sqlite3.connect(root / "wreckscanner.sqlite3")
    try:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM field_photos WHERE id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise AssertionError(f"Missing DB field photo {photo_id}")
    record = dict(row)
    record["redactions"] = json.loads(record.pop("redactions_json"))
    record["exif"] = json.loads(record.pop("exif_json"))
    record["links"] = json.loads(record.pop("links_json"))
    return record


class PhotoRetentionTests(unittest.TestCase):
    def test_replaces_old_approved_field_private_original_with_public_copy(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            (root / "wrecks").mkdir()
            photo_id = "photo_20251101T100000Z_abcdef12"
            record_dir = field_dir / photo_id
            record = field_record(photo_id)
            record["public_image_file"] = "public.jpg"
            record["public_thumb_file"] = "public_thumb.jpg"
            write_json(record_dir / "record.json", record)
            write_jpeg(private_dir / record["private_original_file"], color=(255, 0, 0))
            write_jpeg(record_dir / "public.jpg", color=(15, 23, 42))
            write_jpeg(record_dir / "public_thumb.jpg", size=(24, 16), color=(15, 23, 42))
            migrate_json_to_database(root_dir=root, database_path=root / "wreckscanner.sqlite3", require_backup=False)

            report = retire_private_originals(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                now=NOW,
                dry_run=False,
            )

            self.assertEqual(report["field_photos"]["replaced"], 1)
            updated = db_record(root, photo_id)
            self.assertEqual(updated["private_original_file"], f"field_photos/{photo_id}/retained_public.jpg")
            self.assertEqual(updated["private_original_retention_action"], "replaced_with_public_copy")
            self.assertEqual(updated["private_original_replaced_at"], "2026-06-05T12:00:00Z")
            self.assertEqual(updated["content_type"], "image/jpeg")
            self.assertEqual(updated["format"], "JPEG")
            self.assertFalse((private_dir / f"field_photos/{photo_id}/original.jpg").exists())
            self.assertTrue((private_dir / updated["private_original_file"]).exists())
            self.assertEqual(
                (private_dir / updated["private_original_file"]).read_bytes(),
                (record_dir / "public.jpg").read_bytes(),
            )

    def test_deletes_old_rejected_field_private_original(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            (root / "wrecks").mkdir()
            photo_id = "photo_20251101T100000Z_abcdef12"
            record_dir = field_dir / photo_id
            record = field_record(photo_id, status="rejected")
            write_json(record_dir / "record.json", record)
            write_jpeg(private_dir / record["private_original_file"])
            migrate_json_to_database(root_dir=root, database_path=root / "wreckscanner.sqlite3", require_backup=False)

            report = retire_private_originals(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                now=NOW,
                dry_run=False,
            )

            self.assertEqual(report["field_photos"]["deleted"], 1)
            updated = db_record(root, photo_id)
            self.assertIsNone(updated["private_original_file"])
            self.assertEqual(updated["private_original_retention_action"], "deleted_rejected_original")
            self.assertEqual(updated["private_original_deleted_at"], "2026-06-05T12:00:00Z")
            self.assertFalse((private_dir / f"field_photos/{photo_id}/original.jpg").exists())

    def test_database_failure_restores_private_file_state(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            photo_id = "photo_20251101T100000Z_abcdef12"
            record_dir = field_dir / photo_id
            record = field_record(photo_id)
            record["public_image_file"] = "public.jpg"
            record["public_thumb_file"] = "public_thumb.jpg"
            write_json(record_dir / "record.json", record)
            original_path = private_dir / record["private_original_file"]
            write_jpeg(original_path, color=(255, 0, 0))
            write_jpeg(record_dir / "public.jpg", color=(15, 23, 42))
            write_jpeg(record_dir / "public_thumb.jpg", size=(24, 16), color=(15, 23, 42))
            migrate_json_to_database(root_dir=root, database_path=root / "wreckscanner.sqlite3", require_backup=False)

            with (
                patch("core.photo_retention.save_field_photo_record", side_effect=OSError("database failed")),
                self.assertRaisesRegex(OSError, "database failed"),
            ):
                retire_private_originals(
                    field_photos_dir=field_dir,
                    private_photos_dir=private_dir,
                    now=NOW,
                    dry_run=False,
                )

            self.assertTrue(original_path.exists())
            self.assertFalse(original_path.with_name("retained_public.jpg").exists())

    def test_skips_recent_or_pending_private_originals(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            recent_id = "photo_20260501T100000Z_abcdef12"
            pending_id = "photo_20251101T100000Z_abcdef12"
            for photo_id, record in [
                (recent_id, field_record(recent_id, reviewed_at=RECENT_REVIEWED_AT)),
                (pending_id, field_record(pending_id, status="pending", reviewed_at="")),
            ]:
                record_dir = field_dir / photo_id
                if record["public_review_status"] == "approved":
                    record["public_image_file"] = "public.jpg"
                    record["public_thumb_file"] = "public_thumb.jpg"
                    write_jpeg(record_dir / "public.jpg")
                    write_jpeg(record_dir / "public_thumb.jpg", size=(24, 16))
                write_json(record_dir / "record.json", record)
                write_jpeg(private_dir / record["private_original_file"])
            migrate_json_to_database(root_dir=root, database_path=root / "wreckscanner.sqlite3", require_backup=False)

            report = retire_private_originals(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                now=NOW,
                dry_run=False,
            )

            self.assertEqual(report["field_photos"]["replaced"], 0)
            self.assertEqual(report["field_photos"]["deleted"], 0)
            self.assertTrue((private_dir / f"field_photos/{recent_id}/original.jpg").exists())
            self.assertTrue((private_dir / f"field_photos/{pending_id}/original.jpg").exists())

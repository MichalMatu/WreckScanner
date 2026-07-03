import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from core.field_photos import list_field_photos
from core.json_io import write_json_atomic
from scripts.migrate_legacy_wreck_photos import migrate


def image_bytes() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), (90, 120, 150)).save(out, "JPEG")
    return out.getvalue()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, payload)


class LegacyWreckPhotoMigrationTests(unittest.TestCase):
    def test_migrates_attached_photos_to_visible_field_photos(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrecks_dir = root / "zidentyfikowane_wraki"
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            wreck_id = "wreck_51100000_17200000"
            new_photo_id = "photo_20260603T170858Z_51a3de92"
            existing_photo_id = "photo_20260603T171032Z_ee03e9d3"
            wreck_dir = wrecks_dir / wreck_id
            new_photo_dir = wreck_dir / "photos" / new_photo_id
            new_photo_private = private_dir / "wreck_photos" / wreck_id / new_photo_id / "original.jpg"
            existing_private = private_dir / "field_photos" / existing_photo_id / "original.jpg"
            new_photo_private.parent.mkdir(parents=True)
            existing_private.parent.mkdir(parents=True)
            new_photo_dir.mkdir(parents=True)
            new_photo_private.write_bytes(image_bytes())
            existing_private.write_bytes(image_bytes())
            (new_photo_dir / "public.jpg").write_bytes(image_bytes())
            (new_photo_dir / "public_thumb.jpg").write_bytes(image_bytes())

            write_json(
                field_dir / existing_photo_id / "record.json",
                {
                    "id": existing_photo_id,
                    "created_at": "2026-06-03T17:10:32Z",
                    "original_filename": "existing.jpg",
                    "content_type": "image/jpeg",
                    "format": "JPEG",
                    "size_bytes": existing_private.stat().st_size,
                    "image_width": 40,
                    "image_height": 30,
                    "lat": 51.1,
                    "lon": 17.2,
                    "coordinate_source": "map",
                    "private_original_file": f"field_photos/{existing_photo_id}/original.jpg",
                    "public_review_status": "approved",
                    "redactions": [],
                    "reviewed_at": "2026-06-03T17:12:00Z",
                    "attached_wreck_id": wreck_id,
                    "attached_at": "2026-06-04T10:00:00Z",
                },
            )
            write_json(
                wreck_dir / "record.json",
                {
                    "id": wreck_id,
                    "lat": 51.1,
                    "lon": 17.2,
                    "submission_owner": None,
                    "attached_photos": [
                        {
                            "id": new_photo_id,
                            "created_at": "2026-06-03T17:08:58Z",
                            "original_filename": "teren.jpg",
                            "content_type": "image/jpeg",
                            "format": "JPEG",
                            "size_bytes": new_photo_private.stat().st_size,
                            "image_width": 40,
                            "image_height": 30,
                            "field_photo_lat": 51.1001,
                            "field_photo_lon": 17.2001,
                            "private_original_file": f"wreck_photos/{wreck_id}/{new_photo_id}/original.jpg",
                            "public_image_file": f"photos/{new_photo_id}/public.jpg",
                            "public_thumb_file": f"photos/{new_photo_id}/public_thumb.jpg",
                            "public_review_status": "approved",
                            "redactions": [],
                            "reviewed_at": "2026-06-03T17:09:30Z",
                        },
                        {
                            "id": existing_photo_id,
                            "field_photo_lat": 51.1,
                            "field_photo_lon": 17.2,
                            "private_original_file": f"field_photos/{existing_photo_id}/original.jpg",
                        },
                    ],
                },
            )

            result = migrate(
                wrecks_dir=wrecks_dir,
                field_photos_dir=field_dir,
                private_dir=private_dir,
                dry_run=False,
            )

            self.assertEqual(result["created"], [new_photo_id])
            self.assertEqual(result["normalized"], [existing_photo_id])
            self.assertEqual(result["skipped"], [])
            new_record = json.loads((field_dir / new_photo_id / "record.json").read_text(encoding="utf-8"))
            existing_record = json.loads((field_dir / existing_photo_id / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(new_record["issue_type"], "vehicle")
            self.assertEqual(new_record["private_original_file"], f"field_photos/{new_photo_id}/original.jpg")
            self.assertTrue((private_dir / new_record["private_original_file"]).exists())
            self.assertTrue((field_dir / new_photo_id / "public.jpg").exists())
            self.assertNotIn("attached_wreck_id", existing_record)
            self.assertNotIn("attached_at", existing_record)
            visible_ids = {photo["id"] for photo in list_field_photos(field_dir, private_dir=private_dir)}
            self.assertIn(new_photo_id, visible_ids)
            self.assertIn(existing_photo_id, visible_ids)


if __name__ == "__main__":
    unittest.main()

import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from core import field_photos
from core.field_photos import save_field_photo
from core.uploads import UploadedFile


def image_bytes(fmt: str = "JPEG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (48, 32), (70, 120, 160)).save(out, fmt)
    return out.getvalue()


def upload(data: bytes, filename: str = "teren.jpg") -> UploadedFile:
    return UploadedFile("photo", filename, "image/jpeg", data)


class FieldPhotoUploadTests(unittest.TestCase):
    def test_fully_decodes_image_and_limits_pixels_before_writing(self):
        truncated = image_bytes("JPEG")[:-20]
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp) / "photos"
            private_dir = Path(tmp) / "private"
            with self.assertRaisesRegex(ValueError, "uszkodzonym"):
                save_field_photo(upload(truncated), storage_dir, map_lat=51, map_lon=17, private_dir=private_dir)
            self.assertFalse(storage_dir.exists())
            self.assertFalse(private_dir.exists())

        with (
            TemporaryDirectory() as tmp,
            patch.object(field_photos.config, "MAX_FIELD_PHOTO_PIXELS", 1000),
            self.assertRaisesRegex(ValueError, "rozdzielczość"),
        ):
            save_field_photo(
                upload(image_bytes("PNG"), "large.png"),
                Path(tmp) / "photos",
                map_lat=51,
                map_lon=17,
                private_dir=Path(tmp) / "private",
            )

    def test_cleans_files_when_database_write_fails(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp) / "photos"
            private_dir = Path(tmp) / "private"
            with (
                patch.object(field_photos, "_save_field_record", side_effect=OSError("database failed")),
                patch.object(field_photos, "_delete_field_records"),
                self.assertRaisesRegex(OSError, "database failed"),
            ):
                save_field_photo(
                    upload(image_bytes("PNG"), "photo.png"),
                    storage_dir,
                    map_lat=51,
                    map_lon=17,
                    private_dir=private_dir,
                )

            self.assertFalse(any(storage_dir.iterdir()) if storage_dir.exists() else False)
            self.assertFalse(any(private_dir.rglob("*")) if private_dir.exists() else False)


if __name__ == "__main__":
    unittest.main()

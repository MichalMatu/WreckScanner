import io
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import ExifTags, Image, TiffImagePlugin

from core.config import MAX_FIELD_PHOTO_BYTES
from core.field_photos import (
    discard_field_photo_drafts_by_owner,
    field_photo_asset,
    field_photo_owner_original_asset,
    list_field_photo_review_items,
    list_field_photos,
    list_owner_field_photo_review_items,
    review_field_photo,
    review_field_photo_by_owner,
    save_field_photo,
    submit_field_photos_by_owner,
)
from core.uploads import UploadedFile


def image_bytes(fmt: str = "JPEG", gps: tuple[float, float] | None = None) -> bytes:
    out = io.BytesIO()
    image = Image.new("RGB", (48, 32), (70, 120, 160))
    if gps and fmt.upper() == "JPEG":
        lat, lon = gps
        exif = Image.Exif()
        exif[ExifTags.IFD.GPSInfo] = {
            1: "S" if lat < 0 else "N",
            2: _dms(abs(lat)),
            3: "W" if lon < 0 else "E",
            4: _dms(abs(lon)),
        }
        image.save(out, fmt, exif=exif)
    else:
        image.save(out, fmt)
    return out.getvalue()


def image_bytes_with_invalid_gps() -> bytes:
    out = io.BytesIO()
    exif = Image.Exif()
    exif[ExifTags.IFD.GPSInfo] = {
        1: "N",
        2: (
            TiffImagePlugin.IFDRational(51, 1),
            TiffImagePlugin.IFDRational(1, 0),
            TiffImagePlugin.IFDRational(0, 1),
        ),
        3: "E",
        4: (
            TiffImagePlugin.IFDRational(17, 1),
            TiffImagePlugin.IFDRational(0, 1),
            TiffImagePlugin.IFDRational(0, 1),
        ),
    }
    Image.new("RGB", (48, 32), (70, 120, 160)).save(out, "JPEG", exif=exif)
    return out.getvalue()


def _dms(value: float):
    degrees = int(value)
    minutes_float = (value - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60, 4)
    return (
        TiffImagePlugin.IFDRational(degrees, 1),
        TiffImagePlugin.IFDRational(minutes, 1),
        TiffImagePlugin.IFDRational(int(seconds * 10_000), 10_000),
    )


def upload(data: bytes, filename: str = "teren.jpg", field_name: str = "photo") -> UploadedFile:
    return UploadedFile(field_name=field_name, filename=filename, content_type="image/jpeg", data=data)


def db_record(storage_dir: Path, photo_id: str) -> dict:
    connection = sqlite3.connect(storage_dir / "wreckscanner.sqlite3")
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


def db_record_exists(storage_dir: Path, photo_id: str) -> bool:
    connection = sqlite3.connect(storage_dir / "wreckscanner.sqlite3")
    try:
        row = connection.execute("SELECT 1 FROM field_photos WHERE id = ?", (photo_id,)).fetchone()
        return row is not None
    finally:
        connection.close()


class FieldPhotoTests(unittest.TestCase):
    def test_save_field_photo_uses_map_point_even_when_exif_gps_exists(self):
        with TemporaryDirectory() as tmp:
            result = save_field_photo(
                upload(image_bytes(gps=(51.1, 17.2))),
                Path(tmp),
                map_lat=51.3,
                map_lon=17.4,
                private_dir=Path(tmp) / "private",
            )

            photo = result["photo"]
            self.assertEqual(photo["coordinate_source"], "map")
            self.assertAlmostEqual(photo["lat"], 51.3, places=5)
            self.assertAlmostEqual(photo["lon"], 17.4, places=5)

    def test_save_field_photo_uses_map_point_without_exif_gps(self):
        with TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
            )

            photo = result["photo"]
            record_dir = Path(tmp) / photo["id"]
            record = db_record(Path(tmp), photo["id"])
            self.assertEqual(photo["coordinate_source"], "map")
            self.assertEqual(photo["issue_type"], "vehicle")
            self.assertEqual(record["public_review_status"], "pending")
            self.assertEqual(record["private_original_file"], f"field_photos/{photo['id']}/original.png")
            self.assertNotIn("original_file", record)
            self.assertTrue((private_dir / record["private_original_file"]).exists())
            self.assertEqual(record["issue_type"], "vehicle")
            self.assertEqual(record["vehicle_insurance_status"], "unknown")
            self.assertIsNone(record.get("vehicle_insurance_checked_at"))
            self.assertEqual(photo["vehicle_insurance_status"], "unknown")
            self.assertIsNone(photo.get("vehicle_insurance_checked_at"))
            self.assertFalse((record_dir / "public.jpg").exists())
            pending_list = list_field_photos(Path(tmp), private_dir=private_dir)
            self.assertEqual(len(pending_list), 1)
            self.assertEqual(pending_list[0]["public_review_status"], "pending")
            self.assertEqual(pending_list[0]["vehicle_insurance_status"], "unknown")
            self.assertNotIn("public_image", pending_list[0])
            self.assertNotIn("public_thumb", pending_list[0])

    def test_field_photo_edit_token_unlocks_owner_review_without_plaintext_storage(self):
        with TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            token = "owner-token-123"
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
            )
            photo_id = result["photo"]["id"]
            record = db_record(Path(tmp), photo_id)
            record_text = json.dumps(record)

            self.assertNotIn(token, record_text)
            self.assertIn("edit_token_hash", record)
            self.assertIn("edit_token_salt", record)
            with self.assertRaises(PermissionError):
                list_owner_field_photo_review_items([photo_id], "wrong-token", Path(tmp), private_dir=private_dir)

            items = list_owner_field_photo_review_items([photo_id], token, Path(tmp), private_dir=private_dir)
            original_path, content_type = field_photo_owner_original_asset(
                photo_id,
                token,
                Path(tmp),
                private_dir=private_dir,
            )

            self.assertEqual([item["photo_id"] for item in items], [photo_id])
            self.assertEqual(content_type, "image/png")
            self.assertTrue(original_path.exists())

    def test_public_draft_is_hidden_until_owner_submits_for_review(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
                public_review_status="draft",
            )
            photo_id = result["photo"]["id"]

            self.assertEqual(result["photo"]["public_review_status"], "draft")
            self.assertEqual(list_field_photos(storage_dir, private_dir=private_dir), [])
            self.assertEqual(list_field_photo_review_items(storage_dir, private_dir=private_dir), [])

            owner_result = review_field_photo_by_owner(
                photo_id,
                token,
                storage_dir,
                redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
                private_dir=private_dir,
            )
            self.assertEqual(owner_result["photo"]["public_review_status"], "draft")
            self.assertEqual(list_field_photos(storage_dir, private_dir=private_dir), [])
            self.assertEqual(list_field_photo_review_items(storage_dir, private_dir=private_dir), [])

            submit_result = submit_field_photos_by_owner([photo_id], token, storage_dir, private_dir=private_dir)
            record = db_record(storage_dir, photo_id)

            self.assertEqual(submit_result["photos"][0]["public_review_status"], "pending")
            self.assertEqual(record["public_review_status"], "pending")
            self.assertTrue(record["submitted_at"])
            public_list = list_field_photos(storage_dir, private_dir=private_dir)
            self.assertEqual(len(public_list), 1)
            self.assertEqual(public_list[0]["submitted_at"], record["submitted_at"])
            self.assertEqual(len(list_field_photo_review_items(storage_dir, private_dir=private_dir)), 1)

    def test_owner_can_discard_draft_but_not_pending_photo(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
                public_review_status="draft",
            )
            photo_id = result["photo"]["id"]
            private_original = private_dir / f"field_photos/{photo_id}/original.png"

            discard_result = discard_field_photo_drafts_by_owner(
                [photo_id], token, storage_dir, private_dir=private_dir
            )

            self.assertEqual(discard_result["deleted"], [photo_id])
            self.assertFalse(db_record_exists(storage_dir, photo_id))
            self.assertFalse(private_original.exists())
            self.assertFalse(private_original.parent.exists())

            pending_result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
                public_review_status="draft",
            )
            pending_photo_id = pending_result["photo"]["id"]
            submit_field_photos_by_owner([pending_photo_id], token, storage_dir, private_dir=private_dir)

            with self.assertRaises(PermissionError):
                discard_field_photo_drafts_by_owner([pending_photo_id], token, storage_dir, private_dir=private_dir)
            self.assertTrue(db_record_exists(storage_dir, pending_photo_id))

    def test_owner_review_saves_redactions_as_pending_for_admin_decision(self):
        with TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            token = "owner-token-123"
            result = save_field_photo(
                upload(image_bytes(gps=(51.1, 17.2))),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
            )
            photo_id = result["photo"]["id"]
            review_field_photo(photo_id, Path(tmp), status="approved", redactions=[], private_dir=private_dir)

            owner_result = review_field_photo_by_owner(
                photo_id,
                token,
                Path(tmp),
                redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
                private_dir=private_dir,
            )
            record = db_record(Path(tmp), photo_id)

            self.assertEqual(owner_result["photo"]["public_review_status"], "pending")
            self.assertEqual(record["public_review_status"], "pending")
            self.assertEqual(len(record["redactions"][0]["points"]), 4)
            self.assertTrue(record["owner_redactions_updated_at"])
            self.assertFalse((Path(tmp) / photo_id / "public.jpg").exists())

    def test_review_field_photo_generates_redacted_public_copy_without_exif(self):
        with TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            result = save_field_photo(
                upload(image_bytes(gps=(51.1, 17.2))),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                submission_owner="public:owner-session",
                edit_token="owner-secret-token",
            )
            photo_id = result["photo"]["id"]

            review_field_photo(
                photo_id,
                Path(tmp),
                status="approved",
                redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
                private_dir=private_dir,
            )

            public_list = list_field_photos(Path(tmp), private_dir=private_dir)
            self.assertEqual(len(public_list), 1)
            record = db_record(Path(tmp), photo_id)
            self.assertEqual(public_list[0]["public_review_status"], "approved")
            self.assertEqual(list(record["redactions"][0]), ["points"])
            self.assertEqual(len(record["redactions"][0]["points"]), 4)
            self.assertIn("public_image", public_list[0])
            self.assertIn("public_thumb", public_list[0])
            self.assertNotIn("original_url", public_list[0])
            self.assertNotIn("private_original_file", public_list[0])
            self.assertNotIn("submission_owner", public_list[0])
            self.assertNotIn("edit_token_hash", public_list[0])
            self.assertNotIn("edit_token_salt", public_list[0])
            self.assertNotIn("edit_token_created_at", public_list[0])
            self.assertNotIn("owner-secret-token", json.dumps(public_list[0]))
            public_path, public_type = field_photo_asset(photo_id, Path(tmp), "public-image", private_dir=private_dir)
            thumb_path, _ = field_photo_asset(photo_id, Path(tmp), "public-thumb", private_dir=private_dir)
            original_path, _ = field_photo_asset(photo_id, Path(tmp), "original", private_dir=private_dir)
            self.assertEqual(public_type, "image/jpeg")
            self.assertTrue(public_path.exists())
            self.assertTrue(thumb_path.exists())
            self.assertTrue(original_path.exists())
            with Image.open(public_path) as public:
                self.assertEqual(public.getexif(), {})
                self.assertNotEqual(public.getpixel((1, 1)), (70, 120, 160))

    def test_rejected_field_photo_is_removed_from_map_list(self):
        with TemporaryDirectory() as tmp:
            private_dir = Path(tmp) / "private"
            result = save_field_photo(
                upload(image_bytes(gps=(51.1, 17.2))),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
            )
            photo_id = result["photo"]["id"]

            review_field_photo(photo_id, Path(tmp), status="rejected", redactions=[], private_dir=private_dir)

            self.assertEqual(list_field_photos(Path(tmp), private_dir=private_dir), [])

    def test_save_field_photo_stores_supported_issue_type(self):
        with TemporaryDirectory() as tmp:
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                issue_type="infrastructure",
                private_dir=Path(tmp) / "private",
            )

            photo = result["photo"]
            record = db_record(Path(tmp), photo["id"])
            self.assertEqual(photo["issue_type"], "infrastructure")
            self.assertEqual(record["issue_type"], "infrastructure")
            self.assertEqual(photo["vehicle_insurance_status"], "unknown")

    def test_save_field_photo_rejects_unknown_issue_type(self):
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "typ pinezki"):
            save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                issue_type="other",
                private_dir=Path(tmp) / "private",
            )

    def test_vehicle_insurance_status_is_stored_and_editable_for_vehicle_photos(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            result = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                vehicle_insurance_status="uninsured",
            )
            photo_id = result["photo"]["id"]

            self.assertEqual(result["photo"]["vehicle_insurance_status"], "uninsured")
            self.assertRegex(result["photo"]["vehicle_insurance_checked_at"], r"^20\d{2}-")
            self.assertEqual(db_record(storage_dir, photo_id)["vehicle_insurance_status"], "uninsured")
            self.assertRegex(db_record(storage_dir, photo_id)["vehicle_insurance_checked_at"], r"^20\d{2}-")

            review_result = review_field_photo(
                photo_id,
                storage_dir,
                status="approved",
                redactions=[],
                vehicle_insurance_status="insured",
                private_dir=private_dir,
            )
            public_list = list_field_photos(storage_dir, private_dir=private_dir)

            self.assertEqual(review_result["photo"]["vehicle_insurance_status"], "insured")
            self.assertRegex(review_result["photo"]["vehicle_insurance_checked_at"], r"^20\d{2}-")
            self.assertEqual(db_record(storage_dir, photo_id)["vehicle_insurance_status"], "insured")
            self.assertRegex(db_record(storage_dir, photo_id)["vehicle_insurance_checked_at"], r"^20\d{2}-")
            self.assertEqual(public_list[0]["vehicle_insurance_status"], "insured")
            self.assertRegex(public_list[0]["vehicle_insurance_checked_at"], r"^20\d{2}-")

            unknown_result = review_field_photo(
                photo_id,
                storage_dir,
                status="approved",
                redactions=[],
                vehicle_insurance_status="unknown",
                private_dir=private_dir,
            )

            self.assertEqual(unknown_result["photo"]["vehicle_insurance_status"], "unknown")
            self.assertIsNone(unknown_result["photo"]["vehicle_insurance_checked_at"])
            self.assertIsNone(db_record(storage_dir, photo_id)["vehicle_insurance_checked_at"])

    def test_admin_vehicle_insurance_status_updates_same_vehicle_group(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            first = save_field_photo(
                upload(image_bytes("PNG"), filename="pierwsze.png"),
                storage_dir,
                map_lat="51.300000",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            same_group = save_field_photo(
                upload(image_bytes("PNG"), filename="drugie.png"),
                storage_dir,
                map_lat="51.300004",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            other_vehicle = save_field_photo(
                upload(image_bytes("PNG"), filename="daleko.png"),
                storage_dir,
                map_lat="51.300030",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            infrastructure = save_field_photo(
                upload(image_bytes("PNG"), filename="infra.png"),
                storage_dir,
                map_lat="51.300000",
                map_lon="17.400000",
                issue_type="infrastructure",
                private_dir=private_dir,
            )["photo"]["id"]

            result = review_field_photo(
                first,
                storage_dir,
                status="approved",
                redactions=[],
                vehicle_insurance_status="insured",
                private_dir=private_dir,
            )

            self.assertEqual(set(result["vehicle_insurance_updated_photo_ids"]), {first, same_group})
            self.assertEqual(db_record(storage_dir, first)["vehicle_insurance_status"], "insured")
            self.assertEqual(db_record(storage_dir, same_group)["vehicle_insurance_status"], "insured")
            self.assertRegex(db_record(storage_dir, first)["vehicle_insurance_checked_at"], r"^20\d{2}-")
            self.assertEqual(
                db_record(storage_dir, first)["vehicle_insurance_checked_at"],
                db_record(storage_dir, same_group)["vehicle_insurance_checked_at"],
            )
            self.assertEqual(db_record(storage_dir, other_vehicle)["vehicle_insurance_status"], "unknown")
            self.assertIsNone(db_record(storage_dir, other_vehicle).get("vehicle_insurance_checked_at"))
            self.assertEqual(db_record(storage_dir, infrastructure)["vehicle_insurance_status"], "unknown")
            self.assertIsNone(db_record(storage_dir, infrastructure).get("vehicle_insurance_checked_at"))

    def test_owner_vehicle_insurance_update_does_not_touch_neighboring_photos(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"
            first = save_field_photo(
                upload(image_bytes("PNG"), filename="moje.png"),
                storage_dir,
                map_lat="51.300000",
                map_lon="17.400000",
                private_dir=private_dir,
                edit_token=token,
            )["photo"]["id"]
            neighbor = save_field_photo(
                upload(image_bytes("PNG"), filename="sasiednie.png"),
                storage_dir,
                map_lat="51.300004",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]

            review_field_photo_by_owner(
                first,
                token,
                storage_dir,
                redactions=[],
                vehicle_insurance_status="uninsured",
                private_dir=private_dir,
            )

            self.assertEqual(db_record(storage_dir, first)["vehicle_insurance_status"], "uninsured")
            self.assertRegex(db_record(storage_dir, first)["vehicle_insurance_checked_at"], r"^20\d{2}-")
            self.assertEqual(db_record(storage_dir, neighbor)["vehicle_insurance_status"], "unknown")
            self.assertIsNone(db_record(storage_dir, neighbor).get("vehicle_insurance_checked_at"))

    def test_vehicle_insurance_status_is_vehicle_only(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Status OC"):
                save_field_photo(
                    upload(image_bytes("PNG"), filename="teren.png"),
                    Path(tmp),
                    map_lat="51.3",
                    map_lon="17.4",
                    issue_type="infrastructure",
                    private_dir=Path(tmp) / "private",
                    vehicle_insurance_status="insured",
                )

            with self.assertRaisesRegex(ValueError, "status OC"):
                save_field_photo(
                    upload(image_bytes("PNG"), filename="teren.png"),
                    Path(tmp),
                    map_lat="51.3",
                    map_lon="17.4",
                    private_dir=Path(tmp) / "private",
                    vehicle_insurance_status="maybe",
                )

    def test_save_field_photo_uses_map_point_for_invalid_exif_gps(self):
        with TemporaryDirectory() as tmp:
            result = save_field_photo(
                upload(image_bytes_with_invalid_gps()),
                Path(tmp),
                map_lat="51.3",
                map_lon="17.4",
                private_dir=Path(tmp) / "private",
            )

            photo = result["photo"]
            self.assertEqual(photo["coordinate_source"], "map")
            self.assertEqual(photo["lat"], 51.3)
            self.assertEqual(photo["lon"], 17.4)

    def test_save_field_photo_rejects_missing_coordinates(self):
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "Wskaż punkt zdjęcia"):
            save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"), Path(tmp), private_dir=Path(tmp) / "private"
            )

    def test_save_field_photo_validates_size_type_and_field(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "10 MB"):
                save_field_photo(
                    upload(b"x" * (MAX_FIELD_PHOTO_BYTES + 1), "big.jpg"),
                    Path(tmp),
                    private_dir=Path(tmp) / "private",
                )

            with self.assertRaisesRegex(ValueError, "Dozwolone"):
                save_field_photo(
                    upload(image_bytes("GIF"), "teren.gif"),
                    Path(tmp),
                    map_lat=51,
                    map_lon=17,
                    private_dir=Path(tmp) / "private",
                )

            with self.assertRaisesRegex(ValueError, "photo"):
                save_field_photo(
                    upload(image_bytes("JPEG"), field_name="photos[]"),
                    Path(tmp),
                    map_lat=51,
                    map_lon=17,
                    private_dir=Path(tmp) / "private",
                )

            with self.assertRaisesRegex(ValueError, "obsługiwanym zdjęciem"):
                save_field_photo(
                    upload(b"not an image", "bad.jpg"),
                    Path(tmp),
                    map_lat=51,
                    map_lon=17,
                    private_dir=Path(tmp) / "private",
                )


if __name__ == "__main__":
    unittest.main()

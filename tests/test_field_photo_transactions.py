import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.field_photo_owner_actions import delete_field_photos_by_owner
from core.field_photos import review_field_photo, save_field_photo, submit_field_photos_by_owner
from tests.test_field_photos import db_record, db_record_exists, image_bytes, upload


def install_failure_trigger(storage_dir: Path, *, operation: str, photo_id: str) -> None:
    operation_upper = operation.upper()
    if operation_upper not in {"DELETE", "UPDATE"}:
        raise ValueError("Unsupported trigger operation.")
    connection = sqlite3.connect(storage_dir / "wreckscanner.sqlite3")
    try:
        connection.execute("CREATE TABLE mutation_failures (photo_id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO mutation_failures (photo_id) VALUES (?)", (photo_id,))
        connection.execute(
            f"""
            CREATE TRIGGER force_field_photo_{operation.lower()}_failure
            BEFORE {operation_upper} ON field_photos
            WHEN EXISTS (
                SELECT 1 FROM mutation_failures WHERE photo_id = OLD.id
            )
            BEGIN
                SELECT RAISE(ABORT, 'forced field photo mutation failure');
            END
            """
        )
        connection.commit()
    finally:
        connection.close()


class FieldPhotoTransactionTests(unittest.TestCase):
    def test_owner_batch_submit_rolls_back_every_draft_on_database_failure(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"
            photo_ids = [
                save_field_photo(
                    upload(image_bytes("PNG"), filename=f"draft-{index}.png"),
                    storage_dir,
                    map_lat=51.3 + index / 1000,
                    map_lon=17.4,
                    private_dir=private_dir,
                    edit_token=token,
                    public_review_status="draft",
                )["photo"]["id"]
                for index in range(2)
            ]
            install_failure_trigger(storage_dir, operation="update", photo_id=photo_ids[1])

            with self.assertRaisesRegex(sqlite3.IntegrityError, "forced field photo mutation failure"):
                submit_field_photos_by_owner(photo_ids, token, storage_dir, private_dir=private_dir)

            self.assertEqual(
                [db_record(storage_dir, photo_id)["public_review_status"] for photo_id in photo_ids],
                ["draft", "draft"],
            )

    def test_review_restores_public_derivatives_when_database_update_fails(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            photo_id = save_field_photo(
                upload(image_bytes("PNG"), filename="review.png"),
                storage_dir,
                map_lat="51.300000",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            review_field_photo(photo_id, storage_dir, status="approved", redactions=[], private_dir=private_dir)
            record_dir = storage_dir / photo_id
            public_path = record_dir / "public.jpg"
            thumb_path = record_dir / "public_thumb.jpg"
            original_public = public_path.read_bytes()
            original_thumb = thumb_path.read_bytes()
            install_failure_trigger(storage_dir, operation="update", photo_id=photo_id)

            with self.assertRaisesRegex(sqlite3.IntegrityError, "forced field photo mutation failure"):
                review_field_photo(
                    photo_id,
                    storage_dir,
                    status="approved",
                    redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
                    private_dir=private_dir,
                )

            self.assertEqual(public_path.read_bytes(), original_public)
            self.assertEqual(thumb_path.read_bytes(), original_thumb)
            self.assertEqual(db_record(storage_dir, photo_id)["redactions"], [])
            self.assertEqual(list(record_dir.glob(".*.review-backup-*")), [])

    def test_batch_delete_restores_all_files_and_rows_when_database_delete_fails(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"
            photo_ids = [
                save_field_photo(
                    upload(image_bytes("PNG"), filename=f"photo-{index}.png"),
                    storage_dir,
                    map_lat=51.3 + index / 1000,
                    map_lon=17.4,
                    private_dir=private_dir,
                    edit_token=token,
                    public_review_status="draft",
                )["photo"]["id"]
                for index in range(2)
            ]
            expected_originals: dict[str, tuple[Path, bytes]] = {}
            for photo_id in photo_ids:
                record = db_record(storage_dir, photo_id)
                original = private_dir / str(record["private_original_file"])
                expected_originals[photo_id] = (original, original.read_bytes())
                record_dir = storage_dir / photo_id
                (record_dir / "rollback-marker.txt").write_text(photo_id, encoding="utf-8")
            install_failure_trigger(storage_dir, operation="delete", photo_id=photo_ids[1])

            with self.assertRaisesRegex(sqlite3.IntegrityError, "forced field photo mutation failure"):
                delete_field_photos_by_owner(
                    photo_ids,
                    token,
                    storage_dir,
                    private_dir=private_dir,
                )

            for photo_id in photo_ids:
                self.assertTrue(db_record_exists(storage_dir, photo_id))
                self.assertEqual(
                    (storage_dir / photo_id / "rollback-marker.txt").read_text(encoding="utf-8"),
                    photo_id,
                )
                original, expected_bytes = expected_originals[photo_id]
                self.assertEqual(original.read_bytes(), expected_bytes)
            self.assertEqual(list(storage_dir.rglob("*.deleting-*")), [])

    def test_combined_group_update_rolls_back_every_record_in_one_transaction(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            first = save_field_photo(
                upload(image_bytes("PNG"), filename="first.png"),
                storage_dir,
                map_lat="51.300000",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            same_group = save_field_photo(
                upload(image_bytes("PNG"), filename="second.png"),
                storage_dir,
                map_lat="51.300004",
                map_lon="17.400000",
                private_dir=private_dir,
            )["photo"]["id"]
            install_failure_trigger(storage_dir, operation="update", photo_id=same_group)

            with self.assertRaisesRegex(sqlite3.IntegrityError, "forced field photo mutation failure"):
                review_field_photo(
                    first,
                    storage_dir,
                    vehicle_insurance_status="insured",
                    vehicle_resolution_status="removed",
                    private_dir=private_dir,
                )

            for photo_id in (first, same_group):
                record = db_record(storage_dir, photo_id)
                self.assertEqual(record["vehicle_insurance_status"], "unknown")
                self.assertIsNone(record["vehicle_insurance_checked_at"])
                self.assertEqual(record["vehicle_resolution_status"], "active")
                self.assertIsNone(record["vehicle_resolution_updated_at"])


if __name__ == "__main__":
    unittest.main()

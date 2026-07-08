import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.field_photos import list_field_photos, review_field_photo, save_field_photo
from tests.test_field_photos import db_record, image_bytes, upload


class FieldPhotoVehicleResolutionTests(unittest.TestCase):
    def test_admin_vehicle_resolution_status_updates_same_vehicle_group(self):
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

            review_field_photo(first, storage_dir, status="approved", redactions=[], private_dir=private_dir)
            review_field_photo(same_group, storage_dir, status="approved", redactions=[], private_dir=private_dir)
            result = review_field_photo(
                first,
                storage_dir,
                vehicle_resolution_status="removed",
                private_dir=private_dir,
            )

            self.assertEqual(set(result["vehicle_resolution_updated_photo_ids"]), {first, same_group})
            self.assertEqual(db_record(storage_dir, first)["vehicle_resolution_status"], "removed")
            self.assertEqual(db_record(storage_dir, same_group)["vehicle_resolution_status"], "removed")
            self.assertRegex(db_record(storage_dir, first)["vehicle_resolution_updated_at"], r"^20\d{2}-")
            self.assertEqual(db_record(storage_dir, other_vehicle)["vehicle_resolution_status"], "active")
            self.assertIsNone(db_record(storage_dir, other_vehicle).get("vehicle_resolution_updated_at"))
            self.assertEqual(db_record(storage_dir, infrastructure)["vehicle_resolution_status"], "active")
            self.assertIsNone(db_record(storage_dir, infrastructure).get("vehicle_resolution_updated_at"))
            public_by_id = {photo["id"]: photo for photo in list_field_photos(storage_dir, private_dir=private_dir)}
            self.assertEqual(
                {public_by_id[photo_id]["vehicle_resolution_status"] for photo_id in (first, same_group)},
                {"removed"},
            )
            self.assertEqual(public_by_id[other_vehicle]["vehicle_resolution_status"], "active")

            restored = review_field_photo(
                first,
                storage_dir,
                vehicle_resolution_status="active",
                private_dir=private_dir,
            )

            self.assertEqual(set(restored["vehicle_resolution_updated_photo_ids"]), {first, same_group})
            self.assertEqual(db_record(storage_dir, first)["vehicle_resolution_status"], "active")
            self.assertRegex(db_record(storage_dir, first)["vehicle_resolution_updated_at"], r"^20\d{2}-")

    def test_vehicle_resolution_status_is_vehicle_only(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            infrastructure = save_field_photo(
                upload(image_bytes("PNG"), filename="infra.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                issue_type="infrastructure",
                private_dir=private_dir,
            )["photo"]["id"]
            vehicle = save_field_photo(
                upload(image_bytes("PNG"), filename="teren.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
            )["photo"]["id"]

            with self.assertRaisesRegex(ValueError, "usunięcia"):
                review_field_photo(
                    infrastructure,
                    storage_dir,
                    vehicle_resolution_status="removed",
                    private_dir=private_dir,
                )

            with self.assertRaisesRegex(ValueError, "status usunięcia"):
                review_field_photo(
                    vehicle,
                    storage_dir,
                    vehicle_resolution_status="archived",
                    private_dir=private_dir,
                )


if __name__ == "__main__":
    unittest.main()

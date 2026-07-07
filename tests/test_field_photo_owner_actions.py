import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.field_photo_owner_actions import delete_field_photos_by_owner
from core.field_photos import save_field_photo
from tests.test_field_photos import db_record_exists, image_bytes, upload


class FieldPhotoOwnerActionTests(unittest.TestCase):
    def test_owner_can_delete_draft_and_pending_but_not_reviewed_photos(self):
        with TemporaryDirectory() as tmp:
            storage_dir = Path(tmp)
            private_dir = storage_dir / "private"
            token = "owner-token-123"

            draft_result = save_field_photo(
                upload(image_bytes("PNG"), filename="draft.png"),
                storage_dir,
                map_lat="51.3",
                map_lon="17.4",
                private_dir=private_dir,
                edit_token=token,
                public_review_status="draft",
            )
            pending_result = save_field_photo(
                upload(image_bytes("PNG"), filename="pending.png"),
                storage_dir,
                map_lat="51.4",
                map_lon="17.5",
                private_dir=private_dir,
                edit_token=token,
                public_review_status="pending",
            )
            draft_photo_id = draft_result["photo"]["id"]
            pending_photo_id = pending_result["photo"]["id"]

            deleted_result = delete_field_photos_by_owner(
                [draft_photo_id, pending_photo_id],
                token,
                storage_dir,
                private_dir=private_dir,
            )

            self.assertEqual(deleted_result["deleted"], [draft_photo_id, pending_photo_id])
            self.assertFalse(db_record_exists(storage_dir, draft_photo_id))
            self.assertFalse(db_record_exists(storage_dir, pending_photo_id))

            for status in ("approved", "rejected"):
                result = save_field_photo(
                    upload(image_bytes("PNG"), filename=f"{status}.png"),
                    storage_dir,
                    map_lat="51.3",
                    map_lon="17.4",
                    private_dir=private_dir,
                    edit_token=token,
                    public_review_status=status,
                )
                photo_id = result["photo"]["id"]

                with self.assertRaises(PermissionError):
                    delete_field_photos_by_owner([photo_id], token, storage_dir, private_dir=private_dir)
                self.assertTrue(db_record_exists(storage_dir, photo_id))


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import core.privacy_requests as privacy_requests


class PrivacyRequestDatabaseTests(unittest.TestCase):
    def test_create_list_and_update_privacy_request_in_database(self):
        with TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "wreckscanner.sqlite3"

            with patch.object(privacy_requests, "DATABASE_PATH", database_path):
                created = privacy_requests.create_privacy_request(
                    {"email": "person@example.test", "target": "photo_1", "reason": "remove me"}
                )
                requests = privacy_requests.list_privacy_requests()
                updated = privacy_requests.update_privacy_request(
                    created["request_id"], {"status": "done", "admin_note": "handled"}
                )

            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["id"], created["request_id"])
            self.assertEqual(requests[0]["status"], "new")
            self.assertEqual(updated["request"]["status"], "done")
            self.assertEqual(updated["request"]["admin_note"], "handled")
            self.assertTrue(updated["request"]["handled_at"])

    def test_list_privacy_requests_filters_status(self):
        with TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "wreckscanner.sqlite3"

            with patch.object(privacy_requests, "DATABASE_PATH", database_path):
                first = privacy_requests.create_privacy_request(
                    {"email": "a@example.test", "target": "photo_1", "reason": "remove"}
                )
                privacy_requests.create_privacy_request(
                    {"email": "b@example.test", "target": "photo_2", "reason": "blur"}
                )
                privacy_requests.update_privacy_request(first["request_id"], {"status": "done"})
                done = privacy_requests.list_privacy_requests(status="done")
                new = privacy_requests.list_privacy_requests(status="new")

            self.assertEqual([item["id"] for item in done], [first["request_id"]])
            self.assertEqual(len(new), 1)


if __name__ == "__main__":
    unittest.main()

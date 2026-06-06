import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core import (
    field_photos,
    json_io,
    photo_retention,
    privacy_requests,
    wreck_photo_transfers,
    wrecks_store,
)


class AtomicJsonWriteTests(unittest.TestCase):
    def test_write_json_atomic_writes_complete_json_and_removes_temp_file(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"

            json_io.write_json_atomic(path, {"status": "ok", "items": [1, 2]})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"status": "ok", "items": [1, 2]})
            self.assertFalse(list(path.parent.glob(".record.json.*.tmp")))

    def test_write_json_atomic_preserves_existing_file_when_replace_fails(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            original = {"status": "old"}
            path.write_text(json.dumps(original) + "\n", encoding="utf-8")

            with (
                patch.object(json_io.os, "replace", side_effect=OSError("replace failed")),
                self.assertRaises(OSError),
            ):
                json_io.write_json_atomic(path, {"status": "new"})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)
            self.assertFalse(list(path.parent.glob(".record.json.*.tmp")))

    def test_record_json_helpers_delegate_to_atomic_writer(self):
        helpers = (
            (field_photos, "_write_json"),
            (photo_retention, "_write_json"),
            (privacy_requests, "_write_json"),
            (wreck_photo_transfers, "_write_json"),
            (wrecks_store, "write_json"),
        )

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            for module, helper_name in helpers:
                with self.subTest(module=module.__name__, helper=helper_name):
                    with patch.object(module, "write_json_atomic") as writer:
                        getattr(module, helper_name)(path, {"module": module.__name__})

                    writer.assert_called_once_with(path, {"module": module.__name__})


if __name__ == "__main__":
    unittest.main()

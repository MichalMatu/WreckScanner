import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import core.settings_store as settings_store
from core import json_io
from core.settings_store import (
    public_feature_settings_from_dict,
    public_layer_settings_from_dict,
)


class PublicLayerSettingsTests(unittest.TestCase):
    def test_missing_public_layer_settings_default_to_visible(self):
        self.assertEqual(
            public_layer_settings_from_dict({}),
            {
                "saved_wrecks": True,
                "field_photo_vehicle": True,
                "field_photo_infrastructure": True,
                "field_photo_smoke": True,
                "field_photo_pending": True,
                "cadastral": True,
                "base_map_osm": True,
            },
        )

    def test_public_layer_settings_accept_booleans_per_layer(self):
        self.assertEqual(
            public_layer_settings_from_dict({"saved_wrecks": False, "field_photo_smoke": False}),
            {
                "saved_wrecks": False,
                "field_photo_vehicle": True,
                "field_photo_infrastructure": True,
                "field_photo_smoke": False,
                "field_photo_pending": True,
                "cadastral": True,
                "base_map_osm": True,
            },
        )


class PublicFeatureSettingsTests(unittest.TestCase):
    def test_missing_public_feature_settings_default_to_enabled(self):
        self.assertEqual(
            public_feature_settings_from_dict({}),
            {
                "manual_wrecks": True,
                "photo_uploads": True,
            },
        )

    def test_public_feature_settings_accept_booleans_per_feature(self):
        self.assertEqual(
            public_feature_settings_from_dict({"manual_wrecks": False, "photo_uploads": False}),
            {
                "manual_wrecks": False,
                "photo_uploads": False,
            },
        )


class AppSettingsPersistenceTests(unittest.TestCase):
    def test_save_app_settings_writes_complete_json_file(self):
        with TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"

            with patch.object(settings_store, "SETTINGS_PATH", settings_path):
                saved = settings_store.save_app_settings({"public_layers": {"saved_wrecks": False}})

            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(payload, saved)
            self.assertFalse(list(settings_path.parent.glob(".settings.json.*.tmp")))

    def test_save_app_settings_preserves_existing_file_when_atomic_replace_fails(self):
        with TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            original = {"public_layers": {"saved_wrecks": True}}
            settings_path.write_text(json.dumps(original) + "\n", encoding="utf-8")

            with (
                patch.object(settings_store, "SETTINGS_PATH", settings_path),
                patch.object(json_io.os, "replace", side_effect=OSError("replace failed")),
                self.assertRaises(OSError),
            ):
                settings_store.save_app_settings({"public_layers": {"saved_wrecks": False}})

            self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8")), original)
            self.assertFalse(list(settings_path.parent.glob(".settings.json.*.tmp")))


if __name__ == "__main__":
    unittest.main()

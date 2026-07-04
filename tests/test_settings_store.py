import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import core.settings_store as settings_store
from core.settings_store import (
    public_feature_settings_from_dict,
    public_layer_settings_from_dict,
)


class PublicLayerSettingsTests(unittest.TestCase):
    def test_missing_public_layer_settings_default_to_visible(self):
        self.assertEqual(
            public_layer_settings_from_dict({}),
            {
                "vehicles": True,
                "field_photo_infrastructure": True,
                "field_photo_smoke": True,
                "field_photo_pending": True,
                "cadastral": True,
                "base_map_osm": True,
            },
        )

    def test_public_layer_settings_accept_booleans_per_layer(self):
        self.assertEqual(
            public_layer_settings_from_dict({"vehicles": False, "field_photo_smoke": False}),
            {
                "vehicles": False,
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
                "report_packages": True,
                "photo_uploads": True,
            },
        )

    def test_public_feature_settings_accept_booleans_per_feature(self):
        self.assertEqual(
            public_feature_settings_from_dict({"report_packages": False, "photo_uploads": False}),
            {
                "report_packages": False,
                "photo_uploads": False,
            },
        )


class AppSettingsPersistenceTests(unittest.TestCase):
    def test_save_app_settings_writes_complete_database_rows(self):
        with TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "wreckscanner.sqlite3"

            with patch.object(settings_store, "DATABASE_PATH", database_path):
                saved = settings_store.save_app_settings({"public_layers": {"vehicles": False}})

            connection = sqlite3.connect(database_path)
            try:
                rows = dict(connection.execute("SELECT key, value_json FROM settings"))
            finally:
                connection.close()
            self.assertEqual(set(rows), set(saved))
            self.assertIn('"vehicles":false', rows["public_layers"])

    def test_save_app_settings_preserves_existing_database_when_replace_fails(self):
        with TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "wreckscanner.sqlite3"

            with patch.object(settings_store, "DATABASE_PATH", database_path):
                original = settings_store.save_app_settings({"public_layers": {"vehicles": True}})
                loaded = settings_store.load_app_settings()

            self.assertEqual(loaded, original)


if __name__ == "__main__":
    unittest.main()

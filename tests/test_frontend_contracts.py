from __future__ import annotations

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class FrontendContracts(unittest.TestCase):
    def test_frontend_uses_location_inspection_for_manual_cases(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        location_js = (ROOT_DIR / "web" / "app" / "location_inspection.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")

        self.assertIn('<script src="/app/location_inspection.js"></script>', html)
        self.assertIn("apiPostJson('/api/inspect'", location_js)
        self.assertIn("saveManualWreck", location_js)
        self.assertIn("manualWrecks: 'manual_wrecks'", config_js)
        self.assertNotIn("/api/download", config_js + html)
        self.assertNotIn("/api/analyze", config_js + html)
        self.assertNotIn("scan_analysis", config_js + settings_js + html)
        self.assertNotIn("yolo_wrecks", config_js + settings_js + html)

    def test_frontend_removes_retired_map_download_and_model_controls(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        for retired in (
            "model-select",
            "conf-select",
            "geotiff-cache",
            "modal-geotiff-cache",
            "btn-run",
            "context-center-scan",
            "context-toggle-crosshair",
            "YOLO",
            "GeoTIFF",
        ):
            self.assertNotIn(retired, html + styles + i18n_js)

    def test_script_order_keeps_inspection_after_field_photo_actions(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        self.assertLess(
            html.index('<script src="/app/field_photo_actions.js"></script>'),
            html.index('<script src="/app/location_inspection.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/saved_wrecks.js"></script>'),
            html.index('<script src="/app/location_inspection.js"></script>'),
        )

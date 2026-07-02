import re
import unittest
from pathlib import Path

from app import config as app_config
from core import config as core_config

ROOT_DIR = Path(__file__).resolve().parent.parent


def frontend_map_source_block(config_js: str) -> str:
    match = re.search(r"const MAP_SOURCES = \[(.*?)\];", config_js, re.S)
    if not match:
        raise AssertionError("MAP_SOURCES block not found")
    return match.group(1)


class ConfigModuleContractTests(unittest.TestCase):
    def test_core_and_app_config_modules_expose_shared_runtime_contracts(self):
        self.assertEqual(app_config.HOST, "127.0.0.1")
        self.assertEqual(app_config.PORT, 8001)
        self.assertEqual(core_config.ORTHO_YEARS, [2020, 2021, 2022, 2023, 2024, 2025])
        self.assertEqual(core_config.ORTHO_WMS_BASE, "https://gis1.um.wroc.pl/arcgis/services/ogc")
        self.assertEqual(core_config.ORTHO_CROP_PIXELS_PER_METER, 20.0)
        self.assertEqual(core_config.ORTHO_CROP_MIN_PX, 180)
        self.assertEqual(core_config.ORTHO_CROP_MAX_PX, 800)
        self.assertEqual(core_config.ORTHO_CROP_MAX_WORKERS, 4)
        self.assertEqual(app_config.WMS_UPSTREAM_BASE, core_config.ORTHO_WMS_BASE)
        self.assertEqual(app_config.WMS_TIMEOUT, core_config.ORTHO_WMS_TIMEOUT)
        self.assertTrue(app_config.ADMIN_COOKIE_SECURE)
        self.assertEqual(app_config.CORS_ALLOWED_ORIGINS, ("https://wreckscanner.pl",))

    def test_web_config_is_loaded_before_application_code(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        app_js = (ROOT_DIR / "web" / "app.js").read_text(encoding="utf-8")
        map_helpers_js = (ROOT_DIR / "web" / "map_helpers.js").read_text(encoding="utf-8")

        self.assertLess(html.index('<script src="/config.js"></script>'), html.index('<script src="/app.js"></script>'))
        self.assertLess(
            html.index('<script src="/map_helpers.js"></script>'), html.index('<script src="/app.js"></script>')
        )
        self.assertIn("const MAP_SOURCES = [", config_js)
        self.assertNotIn("ORTHO_YEARS", config_js)
        self.assertIn("key: 'wroclaw-2025'", config_js)
        self.assertIn("shortLabel: '2025'", config_js)
        self.assertIn("key: 'poland-ortho'", config_js)
        self.assertIn("shortLabel: 'POL'", config_js)
        self.assertIn("const GEOPORTAL_STANDARD_WMTS_TILE_URL =", config_js)
        self.assertIn("ORTO/WMTS/StandardResolution", config_js)
        self.assertIn("&LAYER=ORTOFOTOMAPA", config_js)
        self.assertIn("&TILEMATRIX=EPSG:3857:{z}", config_js)
        self.assertNotIn("ORTO/WMS/StandardResolution", config_js)
        self.assertNotIn("key: 'geoportal-high'", config_js)
        self.assertNotIn("shortLabel: 'HIGH'", config_js)
        self.assertNotIn("HighResolution", config_js)
        self.assertNotIn("geoportal-trueortho", config_js)
        self.assertNotIn("PrawdziwaOrtofotomapa", config_js)
        self.assertIn("const DEFAULT_MAP_SOURCE_KEY = 'poland-ortho'", config_js)
        self.assertIn("const MAP_VIEW_STORAGE_KEY = 'wreckscanner.mapView.v2'", config_js)
        self.assertIn("const WELCOME_MODAL_SEEN_STORAGE_KEY = 'wreckscanner.welcomeSeen.v1'", config_js)
        self.assertIn("center: [52.1, 19.4]", config_js)
        self.assertIn("zoom: 7", config_js)
        self.assertIn(
            "const CADASTRAL_WMS_URL = 'https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow'",
            config_js,
        )
        self.assertIn("const CADASTRAL_WMS_LAYERS = 'dzialki,numery_dzialek'", config_js)
        self.assertIn("const CADASTRAL_LAYER_VISIBLE_STORAGE_KEY", config_js)
        self.assertIn("const FIELD_PHOTO_GROUP_RADIUS_M = 1", config_js)
        self.assertIn("const CADASTRAL_IDENTIFY_URL = '/api/cadastral/identify'", config_js)
        self.assertEqual(
            app_config.CADASTRAL_WMS_URL, "https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow"
        )
        self.assertEqual(
            app_config.CADASTRAL_WMS_FALLBACK_URL,
            "https://integracja01.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow",
        )
        self.assertEqual(app_config.CADASTRAL_WMS_TIMEOUT, (10, 30))
        self.assertNotIn("const FIELD_PHOTO_GROUP_RADIUS_M", app_js)
        self.assertIn("function readStoredMapView()", map_helpers_js)
        self.assertIn("new URLSearchParams(window.location.search)", map_helpers_js)
        self.assertIn("params.has('lat') && params.has('lon') && params.has('z')", map_helpers_js)
        self.assertIn("const urlZoom = Number(params.get('z'))", map_helpers_js)
        self.assertIn("function appPlaceUrl(lat, lon, zoom)", map_helpers_js)
        self.assertIn("function squareBounds(start, end)", map_helpers_js)
        self.assertNotIn("function readStoredMapView()", app_js)
        self.assertNotIn("function squareBounds(start, end)", app_js)

    def test_frontend_map_sources_are_structured_and_match_slider_contract(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        block = frontend_map_source_block(config_js)

        keys = re.findall(r"key: '([^']+)'", block)
        short_labels = re.findall(r"shortLabel: '([^']+)'", block)
        default_key = re.search(r"const DEFAULT_MAP_SOURCE_KEY = '([^']+)'", config_js).group(1)

        self.assertEqual(
            keys,
            [
                "wroclaw-2020",
                "wroclaw-2021",
                "wroclaw-2022",
                "wroclaw-2023",
                "wroclaw-2024",
                "wroclaw-2025",
                "openstreetmap",
                "poland-ortho",
            ],
        )
        self.assertEqual(len(short_labels), len(keys))
        self.assertTrue(all(1 <= len(label) <= 4 for label in short_labels))
        self.assertIn(f'max="{len(keys) - 1}"', html)
        self.assertIn(f'value="{keys.index(default_key)}"', html)

        poland_source = re.search(r"\{\s*key: 'poland-ortho'.*?\n\s*\}", block, re.S).group(0)
        self.assertIn("shortLabel: 'POL'", poland_source)
        self.assertIn("type: 'tile'", poland_source)
        self.assertIn("url: GEOPORTAL_STANDARD_WMTS_TILE_URL", poland_source)
        self.assertIn("maxNativeZoom: 19", poland_source)
        self.assertNotIn("layers: 'Raster'", poland_source)
        osm_source = re.search(r"\{\s*key: 'openstreetmap'.*?\n\s*\}", block, re.S).group(0)
        self.assertIn("shortLabel: 'OSM'", osm_source)
        self.assertIn("type: 'tile'", osm_source)
        self.assertIn("labelsOverlay: false", osm_source)
        self.assertIn("publicLayerKey: PUBLIC_LAYER_KEYS.baseMapOsm", osm_source)
        self.assertNotIn("HighResolution", block)
        self.assertNotIn("3,2,1", block)
        self.assertNotIn("TrueOrtho", block)


if __name__ == "__main__":
    unittest.main()

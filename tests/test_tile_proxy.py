import base64
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from app.http import wms_proxy

JPEG_BYTES = b"\xff\xd8\xffjpeg"


class FakeHandler:
    def __init__(self, path: str):
        self.client_address = ("127.0.0.1", 12345)
        self.command = "GET"
        self.headers = {}
        self.path = path
        self.response_headers = []
        self.status = None
        self.wfile = BytesIO()

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None


class FakeResponse:
    def __init__(self, content: bytes = JPEG_BYTES, content_type: str = "image/jpeg"):
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index : index + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


class TileProxyTests(unittest.TestCase):
    WMS_QUERY = (
        "service=WMS&request=GetMap&layers=1&styles=&format=image%2Fpng&transparent=false&version=1.1.1"
        "&width=256&height=256&srs=EPSG%3A3857&bbox=0%2C0%2C100%2C100"
    )

    def test_tile_proxy_reads_enhancement_settings_from_request_token(self):
        token = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "enabled": False,
                        "clahe_clip_limit": 4.2,
                        "clahe_tile_grid_size": 12,
                        "l_percentile_low": 5,
                        "l_percentile_high": 95,
                        "l_output_low": 20,
                        "l_output_high": 230,
                        "decast_strength": 0.75,
                    }
                ).encode("utf-8")
            )
            .decode("ascii")
            .rstrip("=")
        )

        settings = wms_proxy._request_enhancement_settings(f"geoportal-standard/7/65/42?enhancementSettings={token}")

        self.assertFalse(settings.enabled)
        self.assertEqual(settings.clahe_clip_limit, 4.2)
        self.assertEqual(settings.clahe_tile_grid_size, 12)
        self.assertEqual(settings.l_percentile_low, 5)
        self.assertEqual(settings.l_percentile_high, 95)
        self.assertEqual(settings.l_output_low, 20)
        self.assertEqual(settings.l_output_high, 230)
        self.assertEqual(settings.decast_strength, 0.75)

    def test_tile_proxy_uses_default_enhancement_settings_for_invalid_request_token(self):
        settings = wms_proxy._request_enhancement_settings("geoportal-standard/7/65/42?enhancementSettings=bad")

        self.assertFalse(settings.enabled)
        self.assertEqual(settings.clahe_clip_limit, 0.8)
        self.assertEqual(settings.clahe_tile_grid_size, 12)

    def test_geoportal_tile_proxy_builds_standard_wmts_request(self):
        handler = FakeHandler("/tile_proxy/geoportal-standard/7/65/42?enhancementSettings=123")
        session = FakeSession()

        with patch.object(wms_proxy, "_handle_enhanced_tile") as enhanced_tile:
            wms_proxy.handle_geoportal_tile_proxy(handler)

        enhanced_tile.assert_called_once()
        kwargs = enhanced_tile.call_args.kwargs
        self.assertEqual(kwargs["cache_identity"], "geoportal-standard/7/65/42?enhancementSettings=123")
        self.assertEqual(kwargs["raw_content_type"], "image/jpeg")

        with patch.object(wms_proxy.map_downloads, "get_http_session", return_value=session):
            self.assertEqual(kwargs["fetch_raw_tile"]("ignored"), JPEG_BYTES)

        self.assertEqual(len(session.calls), 1)
        url, request_kwargs = session.calls[0]
        self.assertEqual(url, wms_proxy.config.GEOPORTAL_STANDARD_WMTS_URL)
        self.assertEqual(request_kwargs["params"]["SERVICE"], "WMTS")
        self.assertEqual(request_kwargs["params"]["REQUEST"], "GetTile")
        self.assertEqual(request_kwargs["params"]["LAYER"], "ORTOFOTOMAPA")
        self.assertEqual(request_kwargs["params"]["TILEMATRIX"], "EPSG:3857:7")
        self.assertEqual(request_kwargs["params"]["TILECOL"], "65")
        self.assertEqual(request_kwargs["params"]["TILEROW"], "42")

    def test_wms_proxy_accepts_only_configured_getmap_shape(self):
        handler = FakeHandler(f"/wms_proxy/OGC_ortofoto_2025/MapServer/WMSServer?{self.WMS_QUERY}")

        with patch.object(wms_proxy, "_handle_enhanced_tile") as enhanced_tile:
            wms_proxy.handle_wms_proxy(handler)

        enhanced_tile.assert_called_once()
        cache_identity = enhanced_tile.call_args.kwargs["cache_identity"]
        self.assertTrue(cache_identity.startswith("OGC_ortofoto_2025/MapServer/WMSServer?"))
        self.assertIn("request=GetMap", cache_identity)

        invalid_paths = (
            "/wms_proxy/arbitrary/service?" + self.WMS_QUERY,
            "/wms_proxy/OGC_ortofoto_1999/MapServer/WMSServer?" + self.WMS_QUERY,
            "/wms_proxy/OGC_ortofoto_2025/MapServer/WMSServer?" + self.WMS_QUERY + "&width=4096",
            "/wms_proxy/OGC_ortofoto_2025/MapServer/WMSServer?" + self.WMS_QUERY + "&url=https://evil.test",
        )
        for invalid_path in invalid_paths:
            invalid_handler = FakeHandler(invalid_path)
            with (
                self.subTest(invalid_path=invalid_path),
                patch.object(wms_proxy, "_handle_enhanced_tile") as invalid_enhanced_tile,
            ):
                wms_proxy.handle_wms_proxy(invalid_handler)
            self.assertEqual(invalid_handler.status, 400)
            invalid_enhanced_tile.assert_not_called()

    def test_image_response_rejects_oversized_declared_length(self):
        response = FakeResponse()
        response.headers["Content-Length"] = str(wms_proxy._MAX_TILE_BYTES + 1)

        with self.assertRaisesRegex(ValueError, "too large"):
            wms_proxy._read_image_response(response)

    def test_geoportal_tile_proxy_rejects_bad_coordinates(self):
        handler = FakeHandler("/tile_proxy/geoportal-standard/2/4/0")

        wms_proxy.handle_geoportal_tile_proxy(handler)

        self.assertEqual(handler.status, 400)
        self.assertIn(b"Invalid tile coordinates", handler.wfile.getvalue())

    def test_enhanced_tile_returns_no_store_png_fallback_on_upstream_error(self):
        handler = FakeHandler("/tile_proxy/geoportal-standard/7/65/42")

        def fail_fetch(_path: str) -> bytes:
            raise RuntimeError("upstream down")

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(wms_proxy.config, "WMS_TILE_CACHE_DIR", Path(tmp)),
            patch.object(wms_proxy.http_responses, "log_exception") as log_exception,
        ):
            wms_proxy._handle_enhanced_tile(
                handler,
                cache_identity="geoportal-standard/7/65/42",
                fetch_raw_tile=fail_fetch,
                raw_content_type="image/jpeg",
                upstream_error_label="Geoportal WMTS",
            )

        headers = dict(handler.response_headers)
        self.assertEqual(handler.status, 200)
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-WMS-Cache"], "UPSTREAM_ERROR")
        self.assertTrue(handler.wfile.getvalue().startswith(b"\x89PNG\r\n\x1a\n"))
        log_exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()

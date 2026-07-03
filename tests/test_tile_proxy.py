import base64
import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.http import wms_proxy


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
    def __init__(self, content: bytes = b"jpeg"):
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


class TileProxyTests(unittest.TestCase):
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
            self.assertEqual(kwargs["fetch_raw_tile"]("ignored"), b"jpeg")

        self.assertEqual(len(session.calls), 1)
        url, request_kwargs = session.calls[0]
        self.assertEqual(url, wms_proxy.config.GEOPORTAL_STANDARD_WMTS_URL)
        self.assertEqual(request_kwargs["params"]["SERVICE"], "WMTS")
        self.assertEqual(request_kwargs["params"]["REQUEST"], "GetTile")
        self.assertEqual(request_kwargs["params"]["LAYER"], "ORTOFOTOMAPA")
        self.assertEqual(request_kwargs["params"]["TILEMATRIX"], "EPSG:3857:7")
        self.assertEqual(request_kwargs["params"]["TILECOL"], "65")
        self.assertEqual(request_kwargs["params"]["TILEROW"], "42")

    def test_geoportal_tile_proxy_rejects_bad_coordinates(self):
        handler = FakeHandler("/tile_proxy/geoportal-standard/2/4/0")

        wms_proxy.handle_geoportal_tile_proxy(handler)

        self.assertEqual(handler.status, 400)
        self.assertIn(b"Invalid tile coordinates", handler.wfile.getvalue())


if __name__ == "__main__":
    unittest.main()

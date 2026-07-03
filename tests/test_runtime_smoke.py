import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit

from scripts import smoke_runtime


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes):
        self.status = status
        self.headers = headers
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def json_response(payload: dict) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "X-Frame-Options": "SAMEORIGIN",
        },
        json.dumps(payload).encode("utf-8"),
    )


def text_response(content_type: str, body: str) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "Content-Type": content_type,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "X-Frame-Options": "SAMEORIGIN",
        },
        body.encode("utf-8"),
    )


class RuntimeSmokeTests(unittest.TestCase):
    def fake_urlopen(self, req, timeout=5.0):
        path = urlsplit(req.full_url).path
        if path == "/":
            return text_response(
                "text/html; charset=utf-8",
                """
                <div id="map"></div>
                <button id="panel-add-field-photo" onclick="openFieldPhotoUploadFromPanel()" hidden></button>
                <script src="/app/startup.js"></script>
                """,
            )
        if path in {
            "/styles.css",
            "/styles/panel.css",
            "/app.js",
            "/app/api.js",
            "/app/field_photo_upload.js",
            "/app/settings.js",
        }:
            return text_response("text/plain", "asset")
        if path == "/api/health":
            return json_response(
                {
                    "status": "ok",
                    "pressure": {"overloaded": False},
                    "wms_tile_cache": {"count": 1},
                }
            )
        if path == "/api/field-photos":
            return json_response({"status": "ok", "photos": []})
        if path == "/api/__runtime_smoke_missing__":
            raise HTTPError(
                req.full_url,
                404,
                "Not found",
                {
                    "Content-Type": "application/json",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "same-origin",
                    "X-Frame-Options": "SAMEORIGIN",
                },
                io.BytesIO(json.dumps({"error": "missing", "request_id": "abc"}).encode("utf-8")),
            )
        raise AssertionError(path)

    def test_runtime_smoke_checks_landing_assets_health_public_lists_and_json_404(self):
        with patch.object(smoke_runtime, "urlopen", side_effect=self.fake_urlopen):
            checks = smoke_runtime.run_smoke("http://example.test", timeout=1)

        self.assertEqual(
            checks,
            [
                "landing",
                "/styles.css",
                "/styles/panel.css",
                "/app.js",
                "/app/api.js",
                "/app/field_photo_upload.js",
                "/app/settings.js",
                "health",
                "/api/field-photos",
                "api 404",
            ],
        )

    def test_runtime_smoke_rejects_landing_without_primary_photo_cta(self):
        def urlopen_without_cta(req, timeout=5.0):
            if urlsplit(req.full_url).path == "/":
                return text_response("text/html; charset=utf-8", '<div id="map"></div>')
            return self.fake_urlopen(req, timeout=timeout)

        with (
            patch.object(smoke_runtime, "urlopen", side_effect=urlopen_without_cta),
            self.assertRaisesRegex(smoke_runtime.SmokeFailure, "panel-add-field-photo"),
        ):
            smoke_runtime.run_smoke("http://example.test", timeout=1)


if __name__ == "__main__":
    unittest.main()

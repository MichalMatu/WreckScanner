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
            "Content-Security-Policy": "default-src 'self'; object-src 'none'",
            "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "X-Frame-Options": "SAMEORIGIN",
        },
        json.dumps(payload).encode("utf-8"),
    )


def text_response(content_type: str, body: str, *, cache_control: str | None = None) -> FakeResponse:
    headers = {
        "Content-Type": content_type,
        "Content-Security-Policy": "default-src 'self'; object-src 'none'",
        "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
        "X-Frame-Options": "SAMEORIGIN",
    }
    if cache_control:
        headers["Cache-Control"] = cache_control
    return FakeResponse(
        200,
        headers,
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
            "/i18n/pl.js",
            "/i18n/en.js",
            "/i18n.js",
            "/app.js",
            "/app/api.js",
            "/app/field_photo_upload.js",
            "/app/settings.js",
        }:
            return text_response("text/plain", "asset", cache_control="no-store")
        if path == "/api/health/live":
            return json_response({"status": "ok"})
        if path == "/api/health/ready":
            return json_response(
                {
                    "status": "ok",
                    "checks": {"database": {"quick_check": ["ok"]}, "storage": {"free_bytes": 1}},
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
                    "Content-Security-Policy": "default-src 'self'; object-src 'none'",
                    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
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
                "/i18n/pl.js",
                "/i18n/en.js",
                "/i18n.js",
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

    def test_runtime_smoke_rejects_non_http_and_ambiguous_base_urls(self):
        invalid_urls = (
            "file:///tmp/index.html",
            "ftp://example.test",
            "localhost:8001",
            "http:///missing-host",
            "http://user:secret@example.test",
            "https://example.test?target=other",
            "https://example.test#fragment",
            "http://example.test:invalid",
        )

        for base_url in invalid_urls:
            with self.subTest(base_url=base_url), self.assertRaises(smoke_runtime.SmokeFailure):
                smoke_runtime.request(base_url, "/")

        self.assertEqual(
            smoke_runtime.smoke_url("https://example.test/base/", "/api/health/live"),
            "https://example.test/base/api/health/live",
        )


if __name__ == "__main__":
    unittest.main()

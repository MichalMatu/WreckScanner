import json
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from app.http import dispatch, request_body


class FakeHandler:
    def __init__(self, path: str, headers: dict[str, str] | None = None):
        self.client_address = ("127.0.0.1", 12345)
        self.command = "POST"
        self.headers = headers or {}
        self.path = path
        self.rfile = BytesIO(b"{}")
        self.wfile = BytesIO()
        self.status = None
        self.response_headers: list[tuple[str, str]] = []

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None

    @property
    def payload(self) -> dict:
        return json.loads(self.wfile.getvalue())


class HttpRequestSecurityTests(unittest.TestCase):
    def test_cross_site_mutation_is_rejected_before_route(self):
        handler = FakeHandler(
            "/api/settings",
            {
                "Content-Type": "application/json",
                "Content-Length": "2",
                "Host": "wreckscanner.pl",
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )

        with patch.object(dispatch.http_settings, "handle_save_settings") as route:
            dispatch.handle_post(handler)

        self.assertEqual(handler.status, 403)
        self.assertIn("obcego źródła", handler.payload["error"])
        route.assert_not_called()

    def test_same_host_and_configured_origins_are_allowed(self):
        for origin, host in (
            ("https://wreckscanner.pl", "wreckscanner.pl"),
            ("http://127.0.0.1:8001", "127.0.0.1:8001"),
        ):
            handler = FakeHandler("/api/settings", {"Origin": origin, "Host": host})
            self.assertFalse(request_body.reject_unsafe_request(handler))

    def test_cross_site_fetch_metadata_is_rejected_without_origin(self):
        handler = FakeHandler("/api/settings", {"Sec-Fetch-Site": "cross-site"})

        self.assertTrue(request_body.reject_unsafe_request(handler))
        self.assertEqual(handler.status, 403)

    def test_json_dispatch_rejects_plain_text_without_reading_body(self):
        handler = FakeHandler(
            "/api/settings",
            {"Content-Type": "text/plain", "Content-Length": "2"},
        )
        route = Mock()

        request_body.dispatch_json_request(handler, route, handler)

        self.assertEqual(handler.status, 415)
        self.assertIn("application/json", handler.payload["error"])
        route.assert_not_called()

    def test_multipart_routes_reject_wrong_media_type(self):
        handler = FakeHandler(
            "/api/field-photos",
            {"Content-Type": "text/plain", "Content-Length": "2"},
        )

        with patch.object(dispatch.http_public, "handle_create_field_photo") as route:
            dispatch.handle_post(handler)

        self.assertEqual(handler.status, 415)
        route.assert_not_called()

    def test_multipart_reader_distinguishes_payload_too_large(self):
        handler = FakeHandler(
            "/api/field-photos",
            {"Content-Type": "multipart/form-data; boundary=test", "Content-Length": "10"},
        )

        with self.assertRaises(request_body.PayloadTooLargeError):
            request_body.read_multipart_form(handler, 5)


if __name__ == "__main__":
    unittest.main()

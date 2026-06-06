import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.http import dispatch
from app.http import request_body as http_request_body


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

    def payload(self) -> dict:
        return json.loads(self.wfile.getvalue().decode("utf-8"))


class HttpDispatchContractTests(unittest.TestCase):
    def test_get_unknown_api_is_handled_as_json_404(self):
        handler = FakeHandler("/api/missing")

        handled = dispatch.handle_get(handler)

        self.assertTrue(handled)
        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.payload()["error"], "Nie znaleziono endpointu.")

    def test_get_non_api_falls_back_to_static_handler(self):
        handler = FakeHandler("/app.js")

        handled = dispatch.handle_get(handler)

        self.assertFalse(handled)
        self.assertIsNone(handler.status)

    def test_post_settings_uses_json_dispatch_preflight(self):
        handler = FakeHandler("/api/settings")

        with patch.object(http_request_body, "dispatch_json_request") as dispatch_json:
            dispatch.handle_post(handler)

        dispatch_json.assert_called_once_with(handler, dispatch.http_settings.handle_save_settings, handler)

    def test_head_unknown_api_omits_body(self):
        handler = FakeHandler("/api/missing")

        handled = dispatch.handle_head(handler)

        self.assertTrue(handled)
        self.assertEqual(handler.status, 404)
        self.assertEqual(handler.wfile.getvalue(), b"")

    def test_options_sets_empty_response(self):
        handler = FakeHandler("/api/settings")

        with patch.object(handler, "send_header") as send_header:
            dispatch.handle_options(handler)

        self.assertEqual(handler.status, 204)
        send_header.assert_any_call("Content-Length", "0")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app import config
from app.http import admin_session


class FakeHandler:
    def __init__(self, *, headers: dict[str, str] | None = None):
        self.client_address = ("127.0.0.1", 12345)
        self.command = "GET"
        self.headers = headers or {}
        self.path = "/api/admin/status"
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


class HttpAdminSessionContractTests(unittest.TestCase):
    def test_admin_token_comes_from_configured_cookie_name(self):
        handler = FakeHandler(headers={"Cookie": f"other=x; {config.ADMIN_COOKIE_NAME}=token-123"})

        self.assertEqual(admin_session.admin_token_from_cookie(handler), "token-123")

    def test_malformed_cookie_is_ignored(self):
        handler = FakeHandler(headers={"Cookie": "bad; =broken"})

        self.assertIsNone(admin_session.admin_token_from_cookie(handler))

    def test_admin_cookie_secure_flag_depends_on_request_host(self):
        public_handler = FakeHandler(headers={"Host": "wreckscanner.pl"})
        local_handler = FakeHandler(headers={"Host": "localhost:8000"})

        public_cookie = admin_session.admin_cookie_header(public_handler, "token", max_age=60)
        local_cookie = admin_session.admin_cookie_header(local_handler, "token", max_age=60)

        self.assertIn("HttpOnly", public_cookie)
        self.assertIn("SameSite=Lax", public_cookie)
        self.assertIn("Secure", public_cookie)
        self.assertNotIn("Secure", local_cookie)

    def test_require_admin_reports_disabled_admin_without_auth_secret(self):
        handler = FakeHandler(headers={"X-Request-ID": "admin-disabled-req"})

        with patch.object(admin_session.auth, "admin_enabled", return_value=False):
            allowed = admin_session.require_admin(handler)

        self.assertFalse(allowed)
        self.assertEqual(handler.status, 503)
        payload = handler.payload()
        self.assertIn("Panel administratora", payload["error"])
        self.assertEqual(payload["request_id"], "admin-disabled-req")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app import config
from app.http import admin, auth


class FakeHandler:
    def __init__(self, token: str | None = None):
        self.client_address = ("127.0.0.1", 12345)
        self.command = "POST"
        self.headers = {"Host": "ilestoi.pl"}
        if token:
            self.headers["Cookie"] = f"{config.ADMIN_COOKIE_NAME}={token}"
        self.path = "/api/admin/logout"
        self.response_headers = []
        self.status = None
        self.wfile = BytesIO()

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None


class HttpAuthTests(unittest.TestCase):
    def setUp(self):
        with auth._ACTIVE_ADMIN_SESSIONS_LOCK:
            auth._ACTIVE_ADMIN_SESSIONS.clear()

    def tearDown(self):
        with auth._ACTIVE_ADMIN_SESSIONS_LOCK:
            auth._ACTIVE_ADMIN_SESSIONS.clear()

    def test_signed_active_token_is_accepted_and_tampering_is_rejected(self):
        with patch.object(auth, "admin_password", return_value="correct-password"):
            token = auth.make_admin_token("correct-password")

            self.assertTrue(auth.valid_admin_token(token))
            self.assertFalse(auth.valid_admin_token(f"{token[:-1]}0"))

    def test_correctly_signed_but_unregistered_token_is_rejected(self):
        issued_at = str(int(auth.time.time()))
        payload = f"{issued_at}:unregistered-nonce"
        token = f"{payload}:{auth.admin_signature(payload, 'correct-password')}"

        with patch.object(auth, "admin_password", return_value="correct-password"):
            self.assertFalse(auth.valid_admin_token(token))

    def test_expired_token_is_rejected_and_pruned(self):
        issued_at = 1_000_000
        with (
            patch.object(auth, "admin_password", return_value="correct-password"),
            patch.object(auth.time, "time", return_value=issued_at),
        ):
            token = auth.make_admin_token("correct-password")
        with (
            patch.object(auth, "admin_password", return_value="correct-password"),
            patch.object(auth.time, "time", return_value=issued_at + config.ADMIN_SESSION_SECONDS + 1),
        ):
            self.assertFalse(auth.valid_admin_token(token))
        self.assertNotIn(auth._session_digest(token), auth._ACTIVE_ADMIN_SESSIONS)

    def test_logout_revokes_token_so_cookie_replay_fails(self):
        with patch.object(auth, "admin_password", return_value="correct-password"):
            token = auth.make_admin_token("correct-password")
            handler = FakeHandler(token)

            admin.handle_admin_logout(handler)

            self.assertEqual(handler.status, 200)
            self.assertFalse(auth.valid_admin_token(token))
            self.assertEqual(json.loads(handler.wfile.getvalue())["authenticated"], False)
            self.assertTrue(
                any(key == "Set-Cookie" and "Max-Age=0" in value for key, value in handler.response_headers)
            )


if __name__ == "__main__":
    unittest.main()

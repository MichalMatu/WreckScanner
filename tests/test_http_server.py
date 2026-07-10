import http.server
import json
import threading
import unittest
from io import BytesIO
from unittest.mock import patch

from app.http.server import Handler, ReusableHTTPServer


class FakeSocket:
    def __init__(self):
        self.sent = b""
        self.timeout = None
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def shutdown(self, _how) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeHandler:
    def __init__(self):
        self.headers = {}
        self.wfile = BytesIO()
        self.status = None
        self.response_headers = []

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None


class HttpServerTests(unittest.TestCase):
    def test_over_capacity_connection_gets_bounded_503(self):
        server = ReusableHTTPServer.__new__(ReusableHTTPServer)
        server._request_slots = threading.Semaphore(0)
        request = FakeSocket()

        with patch.object(server, "shutdown_request", side_effect=lambda sock: sock.close()):
            server.process_request(request, ("127.0.0.1", 1234))

        headers, body = request.sent.split(b"\r\n\r\n", 1)
        self.assertIn(b"503 Service Unavailable", headers)
        self.assertIn(f"Content-Length: {len(body)}".encode(), headers)
        self.assertEqual(json.loads(body), {"error": "Serwer jest chwilowo przeciążony."})
        self.assertTrue(request.closed)

    def test_accepted_socket_gets_read_timeout(self):
        server = ReusableHTTPServer.__new__(ReusableHTTPServer)
        request = FakeSocket()

        with patch.object(http.server.ThreadingHTTPServer, "get_request", return_value=(request, ("x", 1))):
            returned_request, _ = server.get_request()

        self.assertIs(returned_request, request)
        self.assertEqual(request.timeout, 30)

    def test_access_log_strips_query_string(self):
        handler = Handler.__new__(Handler)
        handler.path = "/api/address/reverse?lat=51.123&lon=17.456"
        handler.command = "GET"
        handler.request_version = "HTTP/1.1"
        handler.requestline = "GET /api/address/reverse?lat=51.123&lon=17.456 HTTP/1.1"

        with patch.object(http.server.BaseHTTPRequestHandler, "log_message") as base_log:
            handler.log_message('"%s" %s', handler.requestline, "200")

        rendered = base_log.call_args.args[1]
        self.assertIn("/api/address/reverse", rendered)
        self.assertNotIn("lat=", rendered)
        self.assertNotIn("lon=", rendered)

    def test_unsupported_mutation_method_returns_json_405(self):
        handler = FakeHandler()

        Handler.do_PUT(handler)

        self.assertEqual(handler.status, 405)
        self.assertEqual(json.loads(handler.wfile.getvalue())["error"], "Metoda HTTP nie jest obsługiwana.")
        self.assertIn(("Allow", "GET, HEAD, POST, PATCH, DELETE, OPTIONS"), handler.response_headers)


if __name__ == "__main__":
    unittest.main()

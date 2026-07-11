import http.client
import http.server
import json
import threading
import unittest
from io import BytesIO
from unittest.mock import patch

from app import config
from app.http import proxy as http_proxy
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


class FakeHandler(Handler):
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        path: str = "/",
        client_host: str = "127.0.0.1",
    ):
        self.client_address = (client_host, 12345)
        self.headers = headers or {}
        self.path = path
        self.close_connection = False
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
    def setUp(self):
        http_proxy._trusted_proxy_networks.cache_clear()

    def tearDown(self):
        http_proxy._trusted_proxy_networks.cache_clear()

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

    def test_trusted_proxy_http_request_redirects_every_public_host_to_https(self):
        path = "/report?lat=51.1&lon=17.2&lang=pl"

        for hostname in config.PUBLIC_HOSTS:
            with self.subTest(hostname=hostname):
                handler = FakeHandler(
                    headers={"Host": hostname, "X-Forwarded-Proto": "http"},
                    path=path,
                )

                self.assertTrue(handler._redirect_insecure_request())

                self.assertEqual(handler.status, 308)
                self.assertIn(("Location", f"https://{hostname}{path}"), handler.response_headers)
                self.assertIn(("Content-Length", "0"), handler.response_headers)
                self.assertIn(("Connection", "close"), handler.response_headers)
                self.assertEqual(handler.wfile.getvalue(), b"")
                self.assertTrue(handler.close_connection)

    def test_insecure_redirect_rejects_untrusted_public_host_values(self):
        for hostname in ("", "attacker.example", "ilestoi.pl@attacker.example", "ilestoi.pl:443", "ilestoi.pl/"):
            with self.subTest(hostname=hostname):
                handler = FakeHandler(
                    headers={"Host": hostname, "X-Forwarded-Proto": "http"},
                )

                self.assertTrue(handler._redirect_insecure_request())

                self.assertEqual(handler.status, 400)
                self.assertFalse(any(key == "Location" for key, _value in handler.response_headers))
                self.assertTrue(handler.close_connection)

    def test_redirect_headers_are_honored_only_from_trusted_proxy(self):
        cases = (
            ({"Host": "ilestoi.pl"}, "127.0.0.1", False, None),
            ({"Host": "ilestoi.pl", "X-Forwarded-Proto": "https"}, "127.0.0.1", False, None),
            ({"Host": "ilestoi.pl", "X-Forwarded-Proto": "http"}, "198.51.100.10", False, None),
            ({"Host": "ilestoi.pl", "X-Forwarded-Proto": "ftp"}, "127.0.0.1", True, 400),
        )

        for headers, client_host, expected_handled, expected_status in cases:
            with self.subTest(headers=headers, client_host=client_host):
                handler = FakeHandler(headers=headers, client_host=client_host)

                self.assertEqual(handler._redirect_insecure_request(), expected_handled)
                self.assertEqual(handler.status, expected_status)

    def test_parse_request_stops_dispatch_after_insecure_redirect(self):
        handler = Handler.__new__(Handler)

        with (
            patch.object(http.server.BaseHTTPRequestHandler, "parse_request", return_value=True),
            patch.object(Handler, "_redirect_insecure_request", return_value=True) as redirect,
        ):
            self.assertFalse(handler.parse_request())

        redirect.assert_called_once_with()

    def test_parse_request_keeps_local_http_requests(self):
        handler = Handler.__new__(Handler)

        with (
            patch.object(http.server.BaseHTTPRequestHandler, "parse_request", return_value=True),
            patch.object(Handler, "_redirect_insecure_request", return_value=False) as redirect,
        ):
            self.assertTrue(handler.parse_request())

        redirect.assert_called_once_with()

    def test_real_post_request_redirects_before_body_dispatch(self):
        server = ReusableHTTPServer(("127.0.0.1", 0), Handler)
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.start()
        connection = http.client.HTTPConnection(*server.server_address, timeout=2)
        try:
            connection.putrequest("POST", "/api/settings?source=map", skip_host=True)
            connection.putheader("Host", "ilestoi.pl")
            connection.putheader("X-Forwarded-Proto", "http")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", "2")
            connection.endheaders(b"{}")

            response = connection.getresponse()

            self.assertEqual(response.status, 308)
            self.assertEqual(response.getheader("Location"), "https://ilestoi.pl/api/settings?source=map")
            self.assertEqual(response.read(), b"")
        finally:
            connection.close()
            server.server_close()
            server_thread.join(timeout=2)

    def test_unsupported_mutation_method_returns_json_405(self):
        handler = FakeHandler()

        Handler.do_PUT(handler)

        self.assertEqual(handler.status, 405)
        self.assertEqual(json.loads(handler.wfile.getvalue())["error"], "Metoda HTTP nie jest obsługiwana.")
        self.assertIn(("Allow", "GET, HEAD, POST, PATCH, DELETE, OPTIONS"), handler.response_headers)


if __name__ == "__main__":
    unittest.main()

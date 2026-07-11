import http.server
import threading
from contextlib import suppress
from urllib.parse import urlsplit, urlunsplit

from app import config
from app.http import dispatch as http_dispatch
from app.http import proxy as http_proxy
from app.http import responses as http_responses
from app.http import static_files as http_static_files


class ReusableHTTPServer(http.server.ThreadingHTTPServer):
    """Threaded HTTP server — pozwala obsługiwać równolegle żądania tile'ów
    z WMS proxy bez blokowania głównego API."""

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, *args, **kwargs):
        self._request_slots = threading.BoundedSemaphore(config.MAX_HTTP_CONCURRENT_REQUESTS)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(config.HTTP_SOCKET_TIMEOUT_SECONDS)
        return request, client_address

    def process_request(self, request, client_address) -> None:
        if not self._request_slots.acquire(blocking=False):
            with suppress(OSError):
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Cache-Control: no-store\r\n"
                    b"X-Content-Type-Options: nosniff\r\n"
                    b"Content-Length: 47\r\n\r\n"
                    b'{"error":"Serwer jest chwilowo przeci\xc4\x85\xc5\xbcony."}'
                )
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves static files and handles the JSON API."""

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        return not self._canonicalize_public_request()

    def _canonicalize_public_request(self) -> bool:
        if not http_proxy.request_from_trusted_proxy(self):
            return False

        forwarded_proto = str(self.headers.get("X-Forwarded-Proto") or "").strip().lower()
        if not forwarded_proto:
            return False
        if forwarded_proto not in {"http", "https"}:
            self.close_connection = True
            http_responses.send_text_error(self, 400, "Nieprawidłowy protokół przekazany przez proxy.")
            return True

        hostname = self._public_request_hostname(forwarded_proto)
        redirect_path = self._redirect_path()
        if hostname is None or redirect_path is None:
            self.close_connection = True
            http_responses.send_text_error(self, 400, "Nieprawidłowy publiczny adres żądania.")
            return True

        path, query = redirect_path
        canonical_path = "/" if path == "/index.html" else path
        raw_host = str(self.headers.get("Host") or "").strip().lower()
        if forwarded_proto == "https" and raw_host == config.CANONICAL_PUBLIC_HOST and canonical_path == path:
            return False

        self.close_connection = True
        self.send_response(308)
        self.send_header(
            "Location",
            urlunsplit(("https", config.CANONICAL_PUBLIC_HOST, canonical_path, query, "")),
        )
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        return True

    def _public_request_hostname(self, forwarded_proto: str) -> str | None:
        raw_host = str(self.headers.get("Host") or "").strip()
        if not raw_host or any(char.isspace() or ord(char) < 33 for char in raw_host):
            return None
        try:
            parsed_host = urlsplit(f"//{raw_host}")
            port = parsed_host.port
        except ValueError:
            return None
        hostname = str(parsed_host.hostname or "").lower().rstrip(".")
        expected_port = 80 if forwarded_proto == "http" else 443
        if (
            parsed_host.username is not None
            or parsed_host.password is not None
            or parsed_host.path
            or parsed_host.query
            or parsed_host.fragment
            or port not in {None, expected_port}
            or hostname not in config.PUBLIC_HOSTS
        ):
            return None
        return hostname

    def _redirect_path(self) -> tuple[str, str] | None:
        raw_target = str(self.path or "")
        if not raw_target or any(ord(char) < 32 for char in raw_target):
            return None
        try:
            parsed_target = urlsplit(raw_target)
        except ValueError:
            return None
        if (
            parsed_target.scheme
            or parsed_target.netloc
            or parsed_target.fragment
            or not parsed_target.path.startswith("/")
        ):
            return None
        return parsed_target.path, parsed_target.query

    def log_message(self, format: str, *args) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path.startswith(("/wms_proxy/", "/tile_proxy/")):
            return
        rendered = format % args
        request_line = getattr(self, "requestline", "")
        if request_line:
            safe_request_line = f"{self.command} {urlsplit(self.path).path} {self.request_version}"
            rendered = rendered.replace(request_line, safe_request_line)
        super().log_message("%s", rendered)

    def translate_path(self, path: str) -> str:
        return http_static_files.translate_path(path)

    def list_directory(self, path: str):
        http_responses.send_text_error(self, 404, "Nie znaleziono pliku.")
        return None

    def end_headers(self):
        for key, value in http_responses.security_response_headers().items():
            self.send_header(key, value)
        for key, value in http_responses.cors_response_headers(self.headers.get("Origin")).items():
            self.send_header(key, value)
        super().end_headers()

    def do_OPTIONS(self):
        http_dispatch.handle_options(self)

    def do_HEAD(self):
        if not http_dispatch.handle_head(self):
            http_responses.send_text_error(self, 404, "Nie znaleziono pliku.", include_body=False)

    def do_GET(self):
        if not http_dispatch.handle_get(self):
            http_responses.send_text_error(self, 404, "Nie znaleziono pliku.")

    def do_DELETE(self):
        http_dispatch.handle_delete(self)

    def do_PATCH(self):
        http_dispatch.handle_patch(self)

    def do_POST(self):
        http_dispatch.handle_post(self)

    def do_PUT(self):
        http_responses.send_method_not_allowed(self)

    def do_TRACE(self):
        http_responses.send_method_not_allowed(self)

    def do_CONNECT(self):
        http_responses.send_method_not_allowed(self)

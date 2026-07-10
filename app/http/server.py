import http.server
import threading
from contextlib import suppress
from urllib.parse import urlsplit

from app import config
from app.http import dispatch as http_dispatch
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

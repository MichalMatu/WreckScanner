import http.server

from app.http import dispatch as http_dispatch
from app.http import responses as http_responses
from app.http import static_files as http_static_files


class ReusableHTTPServer(http.server.ThreadingHTTPServer):
    """Threaded HTTP server — pozwala obsługiwać równolegle żądania tile'ów
    z WMS proxy bez blokowania głównego API."""

    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves static files and handles the download API."""

    def log_message(self, format: str, *args) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path.startswith("/wms_proxy/") or request_path == "/api/download/progress":
            return
        super().log_message(format, *args)

    def translate_path(self, path: str) -> str:
        return http_static_files.translate_path(path)

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
            super().do_HEAD()

    def do_GET(self):
        if not http_dispatch.handle_get(self):
            super().do_GET()

    def do_DELETE(self):
        http_dispatch.handle_delete(self)

    def do_PATCH(self):
        http_dispatch.handle_patch(self)

    def do_POST(self):
        http_dispatch.handle_post(self)

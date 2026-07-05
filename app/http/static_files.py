import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from app import config
from app.http import responses as http_responses

HTML_PAGE_PATHS = {"/", "/index.html", "/privacy", "/report"}
HTML_INCLUDE_RE = re.compile(r"^[ \t]*<!--\s*include:([A-Za-z0-9_./-]+)\s*-->\s*$", re.MULTILINE)
WEB_ASSET_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}


def send_file(
    handler,
    path: Path,
    content_type: str,
    *,
    cache_control: str = "no-store",
    include_body: bool = True,
    download_name: str | None = None,
) -> None:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise FileNotFoundError("Nie znaleziono pliku.") from exc
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache_control)
    if download_name:
        safe_name = Path(str(download_name).replace("\\", "/")).name.replace('"', "")
        encoded_name = quote(safe_name)
        handler.send_header(
            "Content-Disposition", f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{encoded_name}"
        )
    handler.end_headers()
    if include_body:
        http_responses.write_body(handler, body)


def send_bytes(
    handler,
    body: bytes,
    content_type: str,
    *,
    cache_control: str = "no-store",
    include_body: bool = True,
) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache_control)
    handler.end_headers()
    if include_body:
        http_responses.write_body(handler, body)


def send_web_file(handler, file_name: str, *, include_body: bool = True) -> None:
    path = config.WEB_DIR / file_name
    send_file(handler, path, "text/html; charset=utf-8", include_body=include_body)


def safe_web_relative_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise FileNotFoundError("Nieprawidłowa ścieżka partiala HTML.")
    return path


def render_web_template(file_name: str, *, _seen: frozenset[str] = frozenset()) -> str:
    relative_path = safe_web_relative_path(file_name)
    key = relative_path.as_posix()
    if key in _seen:
        raise FileNotFoundError("Wykryto cykliczny include HTML.")
    path = config.WEB_DIR / relative_path
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileNotFoundError("Nie znaleziono pliku HTML.") from exc

    def replace_include(match: re.Match[str]) -> str:
        include_path = safe_web_relative_path(match.group(1)).as_posix()
        return render_web_template(include_path, _seen=_seen | {key})

    return HTML_INCLUDE_RE.sub(replace_include, template)


def send_web_page(handler, file_name: str = "index.html", *, include_body: bool = True) -> None:
    body = render_web_template(file_name).encode("utf-8")
    send_bytes(handler, body, "text/html; charset=utf-8", include_body=include_body)


def translate_path(path: str) -> str:
    request_path = unquote(urlsplit(path).path)
    if request_path == "/":
        return str(config.WEB_DIR / "index.html")

    base_dir = config.WEB_DIR
    relative_path = request_path.lstrip("/")
    parts = [part for part in relative_path.split("/") if part and part not in {".", ".."}]
    return str(base_dir.joinpath(*parts))


def handle_web_page(handler, path: str, *, include_body: bool = True) -> bool:
    if path in HTML_PAGE_PATHS:
        send_web_page(handler, "index.html", include_body=include_body)
        return True
    return False


def handle_web_asset(handler, path: str, *, include_body: bool = True) -> bool:
    if path in HTML_PAGE_PATHS:
        return False
    relative_path = unquote(urlsplit(path).path).lstrip("/")
    try:
        relative = safe_web_relative_path(relative_path)
    except FileNotFoundError:
        return False
    content_type = WEB_ASSET_CONTENT_TYPES.get(relative.suffix.lower())
    if not content_type:
        return False
    asset_path = config.WEB_DIR / relative
    if not asset_path.is_file():
        return False
    send_file(handler, asset_path, content_type, cache_control="no-store", include_body=include_body)
    return True

from pathlib import Path
from urllib.parse import unquote, urlsplit

from app import config
from app.http import responses as http_responses


def send_file(
    handler,
    path: Path,
    content_type: str,
    *,
    cache_control: str = "no-store",
    include_body: bool = True,
) -> None:
    try:
        body = path.read_bytes()
    except OSError as exc:
        raise FileNotFoundError("Nie znaleziono pliku.") from exc
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


def translate_path(path: str) -> str:
    request_path = unquote(urlsplit(path).path)
    if request_path == "/":
        return str(config.WEB_DIR / "index.html")

    if request_path.startswith(f"/{config.ANALYSIS_DIR_NAME}/") or request_path.startswith(f"/{config.WRECKS_ROUTE}/"):
        base_dir = config.ROOT_DIR
        relative_path = request_path.lstrip("/")
    else:
        base_dir = config.WEB_DIR
        relative_path = request_path.lstrip("/")

    parts = [part for part in relative_path.split("/") if part and part not in {".", ".."}]
    return str(base_dir.joinpath(*parts))


def handle_web_page(handler, path: str, *, include_body: bool = True) -> bool:
    if path == "/privacy":
        send_web_file(handler, "privacy.html", include_body=include_body)
        return True
    if path == "/report":
        send_web_file(handler, "report.html", include_body=include_body)
        return True
    return False

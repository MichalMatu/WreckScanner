import json

from app import config
from app.http import responses as http_responses
from core.uploads import UploadedFile, parse_multipart_form


def content_length(handler) -> int:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except (TypeError, ValueError) as exc:
        raise ValueError("Nieprawidłowy nagłówek Content-Length.") from exc
    if length < 0:
        raise ValueError("Nieprawidłowy nagłówek Content-Length.")
    return length


def reject_oversized_json_body(handler) -> bool:
    try:
        length = content_length(handler)
    except ValueError as exc:
        http_responses.send_json(handler, 400, {"error": str(exc)})
        return True
    if length <= config.MAX_JSON_BODY_BYTES:
        return False
    http_responses.send_json(
        handler,
        413,
        {
            "error": f"Payload JSON przekracza limit {config.MAX_JSON_BODY_BYTES} bajtów.",
            "limit_bytes": config.MAX_JSON_BODY_BYTES,
        },
    )
    return True


def dispatch_json_request(handler, route_handler, *args) -> None:
    if reject_oversized_json_body(handler):
        return
    route_handler(*args)


def read_json_body(handler) -> dict:
    length = content_length(handler)
    body = handler.rfile.read(length) if length else b""
    data = json.loads(body.decode("utf-8")) if body.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("Payload musi być obiektem JSON.")
    return data


def read_multipart_form(handler, max_body_bytes: int) -> tuple[dict[str, str], list[UploadedFile]]:
    content_type = handler.headers.get("Content-Type", "")
    length = content_length(handler)
    if length <= 0:
        raise ValueError("Brak danych formularza.")
    if length > max_body_bytes:
        raise ValueError("Formularz przekracza limit rozmiaru pakietu.")
    body = handler.rfile.read(length)
    return parse_multipart_form(content_type, body, max_body_bytes=max_body_bytes)

from __future__ import annotations

from typing import Any


def response_content_type(response: Any) -> str:
    return str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()


def read_limited_response_bytes(response: Any, *, max_bytes: int) -> bytes:
    limit = int(max_bytes)
    if limit <= 0:
        raise ValueError("Limit odpowiedzi upstreamu musi być dodatni.")

    raw_length = str(response.headers.get("Content-Length") or "").strip()
    if raw_length:
        try:
            declared_length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Upstream zwrócił nieprawidłowy Content-Length.") from exc
        if declared_length < 0 or declared_length > limit:
            raise ValueError("Odpowiedź upstreamu przekracza dozwolony rozmiar.")

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > limit:
            raise ValueError("Odpowiedź upstreamu przekracza dozwolony rozmiar.")
        chunks.append(chunk)
    return b"".join(chunks)

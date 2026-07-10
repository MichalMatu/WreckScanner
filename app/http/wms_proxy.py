import base64
import binascii
import json
import logging
import math
import re
import struct
import threading
import zlib
from functools import lru_cache
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

from app import config, map_downloads, wms_cache
from app.http import responses as http_responses
from core.config import BYTES_PER_MIB
from core.enhancement import enhance_orthophoto
from core.settings_store import enhancement_settings_from_dict, enhancement_settings_to_dict

_MAX_PROXY_PATH_CHARS = 2048
_MAX_TILE_BYTES = 8 * BYTES_PER_MIB
_WMS_PATH_RE = re.compile(r"OGC_ortofoto_(\d{4})/MapServer/WMSServer")
_ALLOWED_WMS_QUERY_KEYS = frozenset(
    {
        "service",
        "request",
        "layers",
        "styles",
        "format",
        "transparent",
        "version",
        "width",
        "height",
        "srs",
        "crs",
        "bbox",
        "enhancementsettings",
    }
)
_WEB_MERCATOR_LIMIT = 20_100_000.0
_WMS_REQUEST_SEMAPHORE = threading.BoundedSemaphore(config.WMS_MAX_CONCURRENT_REQUESTS)
_TILE_LOCKS_GUARD = threading.Lock()
_TILE_LOCKS: dict[str, threading.Lock] = {}


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(payload, checksum)
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum & 0xFFFFFFFF)


@lru_cache(maxsize=1)
def _fallback_tile_png() -> bytes:
    width = height = 256
    rgb = bytes((209, 216, 224))
    raw = b"".join(b"\x00" + rgb * width for _ in range(height))
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(raw, level=6)),
            _png_chunk(b"IEND", b""),
        ]
    )


def _normalized_wms_query(query: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    pairs = parse_qsl(query, keep_blank_values=True)
    values: dict[str, str] = {}
    for key, value in pairs:
        lowered = key.lower()
        if lowered not in _ALLOWED_WMS_QUERY_KEYS or lowered in values:
            raise ValueError("Invalid WMS query")
        values[lowered] = value
    return pairs, values


def _validate_wms_operation(values: dict[str, str]) -> None:
    if values.get("service", "").upper() != "WMS" or values.get("request", "").upper() != "GETMAP":
        raise ValueError("Invalid WMS operation")
    if values.get("layers") != "1" or values.get("format", "").lower() != "image/png":
        raise ValueError("Invalid WMS layer or format")
    if values.get("styles", "") not in {"", "default"}:
        raise ValueError("Invalid WMS style")
    if values.get("transparent", "false").lower() not in {"false", "true"}:
        raise ValueError("Invalid WMS transparency")
    if values.get("version", "1.1.1") not in {"1.1.1", "1.3.0"}:
        raise ValueError("Invalid WMS version")


def _validate_wms_geometry(values: dict[str, str]) -> None:
    try:
        width = int(values.get("width", ""))
        height = int(values.get("height", ""))
        bbox = [float(value) for value in values.get("bbox", "").split(",")]
    except ValueError as exc:
        raise ValueError("Invalid WMS tile dimensions") from exc
    if not (1 <= width <= 512 and 1 <= height <= 512):
        raise ValueError("Invalid WMS tile dimensions")
    if len(bbox) != 4 or not all(math.isfinite(value) and abs(value) <= _WEB_MERCATOR_LIMIT for value in bbox):
        raise ValueError("Invalid WMS bounding box")


def _validate_wms_projection_and_enhancement(values: dict[str, str]) -> None:
    projections = [values[key].upper() for key in ("srs", "crs") if key in values]
    if not projections or any(value != "EPSG:3857" for value in projections):
        raise ValueError("Invalid WMS projection")
    token = values.get("enhancementsettings", "")
    if len(token) > 1500 or (token and re.fullmatch(r"[A-Za-z0-9_-]+", token) is None):
        raise ValueError("Invalid enhancement settings")


def _validated_wms_proxy_path(upstream_path: str) -> str:
    if not upstream_path or len(upstream_path) > _MAX_PROXY_PATH_CHARS:
        raise ValueError("Invalid wms_proxy path")
    parts = urlsplit(upstream_path)
    if parts.scheme or parts.netloc or parts.fragment:
        raise ValueError("Invalid wms_proxy path")
    path = parts.path.strip("/")
    match = _WMS_PATH_RE.fullmatch(path)
    if match is None or int(match.group(1)) not in config.WMS_ALLOWED_YEARS:
        raise ValueError("Invalid wms_proxy path")

    pairs, values = _normalized_wms_query(parts.query)
    _validate_wms_operation(values)
    _validate_wms_geometry(values)
    _validate_wms_projection_and_enhancement(values)
    canonical_query = urlencode(sorted((key.lower(), value) for key, value in pairs))
    return f"{path}?{canonical_query}"


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
    )


def _read_image_response(resp) -> bytes:
    resp.raise_for_status()
    content_type = str(resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    if content_type and not content_type.startswith("image/") and content_type != "application/octet-stream":
        raise ValueError(f"Unexpected upstream content type: {content_type}")
    raw_length = str(resp.headers.get("Content-Length") or "").strip()
    if raw_length:
        try:
            declared_length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Invalid upstream Content-Length") from exc
        if declared_length < 0 or declared_length > _MAX_TILE_BYTES:
            raise ValueError("Upstream tile response is too large")

    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > _MAX_TILE_BYTES:
            raise ValueError("Upstream tile response is too large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not _looks_like_image(data):
        raise ValueError("Upstream response is not a supported image")
    return data


def _send_tile_response(
    handler,
    *,
    body: bytes,
    content_type: str,
    cache_status: str,
    cache_control: str = config.WMS_TILE_CACHE_CONTROL,
) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", cache_control)
    handler.send_header("X-WMS-Cache", cache_status)
    handler.end_headers()
    http_responses.write_body(handler, body)


def _send_tile_fallback(handler, *, cache_status: str) -> None:
    _send_tile_response(
        handler,
        body=_fallback_tile_png(),
        content_type="image/png",
        cache_status=cache_status,
        cache_control="no-store",
    )


def _request_enhancement_settings(cache_identity: str):
    token = ""
    for key, value in parse_qsl(urlsplit(cache_identity).query, keep_blank_values=True):
        if key.lower() == "enhancementsettings":
            token = value
            break
    if not token:
        return enhancement_settings_from_dict({})

    try:
        base64_value = token.replace("-", "+").replace("_", "/")
        base64_value += "=" * ((4 - len(base64_value) % 4) % 4)
        raw = json.loads(base64.b64decode(base64_value).decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError):
        raw = {}
    return enhancement_settings_from_dict(raw)


def _handle_enhanced_tile(
    handler,
    *,
    cache_identity: str,
    fetch_raw_tile,
    raw_content_type: str,
    upstream_error_label: str,
) -> None:
    enhancement_settings = _request_enhancement_settings(cache_identity)
    stripped_upstream_path = wms_cache.strip_proxy_only_params(cache_identity)
    enhancement_fingerprint = wms_cache.enhancement_fingerprint(enhancement_settings_to_dict(enhancement_settings))
    cache_key = wms_cache.tile_cache_key(stripped_upstream_path, enhancement_fingerprint)
    cache_path = wms_cache.tile_cache_path(cache_key)
    cached_bytes = wms_cache.read_tile_cache(cache_path)
    if cached_bytes is not None:
        _send_tile_response(handler, body=cached_bytes, content_type="image/png", cache_status="HIT")
        return
    if not _WMS_REQUEST_SEMAPHORE.acquire(blocking=False):
        _send_tile_fallback(handler, cache_status="BUSY")
        return
    with _TILE_LOCKS_GUARD:
        tile_lock = _TILE_LOCKS.setdefault(cache_key, threading.Lock())
    if not tile_lock.acquire(blocking=False):
        _WMS_REQUEST_SEMAPHORE.release()
        _send_tile_fallback(handler, cache_status="IN_FLIGHT")
        return
    try:
        cached_bytes = wms_cache.read_tile_cache(cache_path)
        if cached_bytes is not None:
            _send_tile_response(handler, body=cached_bytes, content_type="image/png", cache_status="HIT")
            return
        try:
            raw_bytes = fetch_raw_tile(stripped_upstream_path)
        except Exception as exc:
            http_responses.log_exception(
                handler,
                f"{upstream_error_label} upstream tile request failed; returning fallback tile",
                exc,
                status=200,
                level=logging.WARNING,
            )
            _send_tile_fallback(handler, cache_status="UPSTREAM_ERROR")
            return
        try:
            import cv2
            import numpy as np
        except ModuleNotFoundError:
            _send_tile_response(handler, body=raw_bytes, content_type=raw_content_type, cache_status="MISS")
            return

        nparr = np.frombuffer(raw_bytes, dtype=np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            _send_tile_response(handler, body=raw_bytes, content_type=raw_content_type, cache_status="MISS")
            return
        try:
            enhanced = enhance_orthophoto(img, settings=enhancement_settings)
        except Exception as exc:
            http_responses.log_exception(
                handler,
                "WMS enhancement failed; returning raw tile",
                exc,
                status=200,
                level=logging.WARNING,
            )
            _send_tile_response(handler, body=raw_bytes, content_type=raw_content_type, cache_status="MISS")
            return

        success, encoded = cv2.imencode(".png", enhanced, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        if not success:
            logging.getLogger(__name__).warning("WMS PNG encoding failed; returning fallback tile")
            _send_tile_fallback(handler, cache_status="ENCODE_ERROR")
            return
        out_bytes = encoded.tobytes()
        wms_cache.write_tile_cache(cache_path, out_bytes)
        wms_cache.cleanup_tile_cache()
        _send_tile_response(handler, body=out_bytes, content_type="image/png", cache_status="MISS")
    finally:
        tile_lock.release()
        _WMS_REQUEST_SEMAPHORE.release()
        with _TILE_LOCKS_GUARD:
            if _TILE_LOCKS.get(cache_key) is tile_lock:
                _TILE_LOCKS.pop(cache_key, None)


def handle_wms_proxy(handler) -> None:
    upstream_path = handler.path[len("/wms_proxy/") :]
    try:
        upstream_path = _validated_wms_proxy_path(upstream_path)
    except ValueError:
        http_responses.send_text_error(handler, 400, "Invalid wms_proxy path")
        return

    def fetch_raw_tile(stripped_upstream_path: str) -> bytes:
        upstream_url = f"{config.WMS_UPSTREAM_BASE}/{stripped_upstream_path}"
        session = map_downloads.get_http_session()
        with session.get(upstream_url, timeout=config.WMS_TIMEOUT, stream=True) as resp:
            return _read_image_response(resp)

    _handle_enhanced_tile(
        handler,
        cache_identity=upstream_path,
        fetch_raw_tile=fetch_raw_tile,
        raw_content_type="image/png",
        upstream_error_label="WMS",
    )


def handle_geoportal_tile_proxy(handler) -> None:
    path = unquote(urlsplit(handler.path).path)
    parts = [part for part in path.split("/") if part]
    if len(parts) != 5 or parts[:2] != ["tile_proxy", "geoportal-standard"]:
        http_responses.send_text_error(handler, 400, "Invalid tile_proxy path")
        return
    try:
        z, x, y = (int(value) for value in parts[2:])
    except ValueError:
        http_responses.send_text_error(handler, 400, "Invalid tile coordinates")
        return
    if not (0 <= z <= 22 and 0 <= x < 2**z and 0 <= y < 2**z):
        http_responses.send_text_error(handler, 400, "Invalid tile coordinates")
        return

    cache_identity = f"geoportal-standard/{z}/{x}/{y}?{urlsplit(handler.path).query}"

    def fetch_raw_tile(_stripped_upstream_path: str) -> bytes:
        session = map_downloads.get_http_session()
        with session.get(
            config.GEOPORTAL_STANDARD_WMTS_URL,
            params={
                "SERVICE": "WMTS",
                "REQUEST": "GetTile",
                "VERSION": "1.0.0",
                "LAYER": "ORTOFOTOMAPA",
                "STYLE": "default",
                "FORMAT": "image/jpeg",
                "TILEMATRIXSET": "EPSG:3857",
                "TILEMATRIX": f"EPSG:3857:{z}",
                "TILEROW": str(y),
                "TILECOL": str(x),
            },
            timeout=config.WMS_TIMEOUT,
            stream=True,
        ) as resp:
            return _read_image_response(resp)

    _handle_enhanced_tile(
        handler,
        cache_identity=cache_identity,
        fetch_raw_tile=fetch_raw_tile,
        raw_content_type="image/jpeg",
        upstream_error_label="Geoportal WMTS",
    )

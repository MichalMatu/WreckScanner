import logging

from app import config, map_downloads, wms_cache
from app.http import responses as http_responses
from core.enhancement import enhance_orthophoto
from core.settings_store import load_enhancement_settings


def handle_wms_proxy(handler) -> None:
    upstream_path = handler.path[len("/wms_proxy/") :]
    if not upstream_path or ".." in upstream_path:
        http_responses.send_text_error(handler, 400, "Invalid wms_proxy path")
        return

    stripped_upstream_path = wms_cache.strip_proxy_only_params(upstream_path)
    enhancement_fingerprint = wms_cache.enhancement_fingerprint()
    cache_key = wms_cache.tile_cache_key(stripped_upstream_path, enhancement_fingerprint)
    cache_path = wms_cache.tile_cache_path(cache_key)
    cached_bytes = wms_cache.read_tile_cache(cache_path)
    if cached_bytes is not None:
        handler.send_response(200)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Content-Length", str(len(cached_bytes)))
        handler.send_header("Cache-Control", config.WMS_TILE_CACHE_CONTROL)
        handler.send_header("X-WMS-Cache", "HIT")
        handler.end_headers()
        http_responses.write_body(handler, cached_bytes)
        return

    upstream_url = f"{config.WMS_UPSTREAM_BASE}/{stripped_upstream_path}"
    try:
        session = map_downloads.get_http_session()
        resp = session.get(upstream_url, timeout=config.WMS_TIMEOUT)
        resp.raise_for_status()
        raw_bytes = resp.content
    except Exception as exc:
        http_responses.log_exception(handler, "WMS upstream request failed", exc, status=502)
        http_responses.send_text_error(handler, 502, "WMS upstream error")
        return

    try:
        import cv2
        import numpy as np
    except ModuleNotFoundError:
        handler.send_response(200)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Content-Length", str(len(raw_bytes)))
        handler.send_header("Cache-Control", config.WMS_TILE_CACHE_CONTROL)
        handler.send_header("X-WMS-Cache", "MISS")
        handler.end_headers()
        wms_cache.write_tile_cache(cache_path, raw_bytes)
        wms_cache.cleanup_tile_cache()
        http_responses.write_body(handler, raw_bytes)
        return

    nparr = np.frombuffer(raw_bytes, dtype=np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        handler.send_response(200)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Content-Length", str(len(raw_bytes)))
        handler.send_header("Cache-Control", config.WMS_TILE_CACHE_CONTROL)
        handler.send_header("X-WMS-Cache", "MISS")
        handler.end_headers()
        wms_cache.write_tile_cache(cache_path, raw_bytes)
        wms_cache.cleanup_tile_cache()
        http_responses.write_body(handler, raw_bytes)
        return

    try:
        enhanced = enhance_orthophoto(img, settings=load_enhancement_settings())
    except Exception as exc:
        http_responses.log_exception(
            handler,
            "WMS enhancement failed; returning raw tile",
            exc,
            status=200,
            level=logging.WARNING,
        )
        handler.send_response(200)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Content-Length", str(len(raw_bytes)))
        handler.send_header("Cache-Control", config.WMS_TILE_CACHE_CONTROL)
        handler.send_header("X-WMS-Cache", "MISS")
        handler.end_headers()
        wms_cache.write_tile_cache(cache_path, raw_bytes)
        wms_cache.cleanup_tile_cache()
        http_responses.write_body(handler, raw_bytes)
        return

    success, encoded = cv2.imencode(".png", enhanced, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not success:
        http_responses.send_text_error(handler, 500, "PNG encoding failed")
        return

    out_bytes = encoded.tobytes()
    handler.send_response(200)
    handler.send_header("Content-Type", "image/png")
    handler.send_header("Content-Length", str(len(out_bytes)))
    handler.send_header("Cache-Control", config.WMS_TILE_CACHE_CONTROL)
    handler.send_header("X-WMS-Cache", "MISS")
    handler.end_headers()
    wms_cache.write_tile_cache(cache_path, out_bytes)
    wms_cache.cleanup_tile_cache()
    http_responses.write_body(handler, out_bytes)

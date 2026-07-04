from app import wms_cache
from app.http import responses as http_responses


def handle_health(handler) -> None:
    try:
        http_responses.send_json(
            handler,
            200,
            {
                "status": "ok",
                "wms_tile_cache": wms_cache.tile_cache_report(),
            },
        )
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Health status lookup failed",
            exc,
            public_error="Nie udało się pobrać statusu serwera.",
        )

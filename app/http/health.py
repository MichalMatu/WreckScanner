from app import pipeline, wms_cache
from app.http import responses as http_responses


def handle_health(handler) -> None:
    try:
        pressure = pipeline.system_pressure()
        status = "degraded" if pressure["overloaded"] else "ok"
        http_responses.send_json(
            handler,
            200,
            {
                "status": status,
                "pressure": pressure,
                "pipeline": pipeline.pipeline_snapshot(),
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

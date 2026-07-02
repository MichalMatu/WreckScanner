from app import config
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from core import config as core_config
from core.map_crops import crop_to_data_url, fetch_location_crops, validate_crop_m
from core.wrecks_identity import validate_coordinates


def handle_inspect(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        lat, lon = validate_coordinates(data.get("lat"), data.get("lon"))
        crop_m = validate_crop_m(data.get("cropM", core_config.REVIEW_CROP_M))
        crops, _metadata = fetch_location_crops(lat, lon, crop_m=crop_m)
        http_responses.send_json(
            handler,
            200,
            {
                "status": "ok",
                "crops": [
                    {
                        "year": crop.label,
                        "data_url": crop_to_data_url(crop, jpeg_quality=config.INSPECT_JPEG_QUALITY),
                    }
                    for crop in crops
                ],
            },
        )

    except (FileNotFoundError, ValueError) as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Manual map crop creation failed",
            exc,
            public_error="Nie udało się przygotować wycinków mapy.",
        )

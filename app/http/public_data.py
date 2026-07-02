from urllib.parse import parse_qs, urlsplit

from app import config, map_downloads
from app.http import access
from app.http import admin_session as http_admin_session
from app.http import responses as http_responses
from core import config as core_config
from core.cadastral import cadastral_feature_info_params, parse_cadastral_feature_info
from core.field_photos import list_field_photos
from core.wrecks import list_wrecks


def handle_field_photos(handler) -> None:
    try:
        photos = list_field_photos(core_config.FIELD_PHOTOS_DIR)
        if not http_admin_session.is_admin(handler):
            photos = [photo for photo in photos if access.public_field_photo_allowed(handler, photo)]
        http_responses.send_json(handler, 200, {"status": "ok", "photos": photos})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo list lookup failed",
            exc,
            public_error="Nie udało się pobrać zdjęć terenowych.",
        )


def handle_cadastral_identify(handler) -> None:
    if not access.require_public_layer(
        handler, "cadastral", "Warstwa dzialek jest teraz wylaczona dla niezalogowanych."
    ):
        return
    query = parse_qs(urlsplit(handler.path).query)
    try:
        lat = float((query.get("lat") or [""])[0])
        lon = float((query.get("lon") or [""])[0])
    except ValueError:
        http_responses.send_json(handler, 400, {"status": "error", "error": "Nieprawidłowe współrzędne."})
        return
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        http_responses.send_json(handler, 400, {"status": "error", "error": "Współrzędne poza zakresem."})
        return

    params = cadastral_feature_info_params(lat, lon)
    last_error: Exception | None = None
    response = None
    for upstream_url in (config.CADASTRAL_WMS_URL, config.CADASTRAL_WMS_FALLBACK_URL):
        try:
            response = map_downloads.get_http_session().get(
                upstream_url,
                params=params,
                timeout=config.CADASTRAL_WMS_TIMEOUT,
            )
            response.raise_for_status()
            break
        except Exception as exc:
            last_error = exc
            response = None
    if response is None:
        http_responses.send_internal_error(
            handler,
            502,
            "Cadastral upstream request failed",
            last_error or RuntimeError("No cadastral response"),
            public_error="Nie udało się pobrać danych działki.",
        )
        return

    response.encoding = "utf-8"
    parcel = parse_cadastral_feature_info(response.text)
    if not parcel.get("parcel_id") and not parcel.get("parcel_number"):
        http_responses.send_json(
            handler, 404, {"status": "not_found", "error": "Nie znaleziono działki w tym punkcie."}
        )
        return
    http_responses.send_json(handler, 200, {"status": "ok", "parcel": parcel})


def handle_get_wrecks(handler) -> None:
    try:
        wrecks = (
            list_wrecks(core_config.WRECKS_DIR, include_pending=http_admin_session.is_admin(handler))
            if access.public_layer_allowed(handler, "saved_wrecks")
            else []
        )
        http_responses.send_json(handler, 200, {"status": "ok", "wrecks": wrecks})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Wreck list lookup failed",
            exc,
            public_error="Nie udało się pobrać spraw pojazdów.",
        )

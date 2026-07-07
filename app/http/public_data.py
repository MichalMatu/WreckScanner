from functools import lru_cache
from typing import Any
from urllib.parse import parse_qs, urlsplit

from app import config, map_downloads
from app.http import access
from app.http import admin_session as http_admin_session
from app.http import responses as http_responses
from core import config as core_config
from core.cadastral import cadastral_feature_info_params, parse_cadastral_feature_info
from core.field_photos import list_field_photos
from core.geo import validate_coordinates
from core.prg_addresses import parse_prg_address_features, prg_address_wfs_params
from core.reverse_geocoding import normalize_reverse_geocode_result


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


def lookup_cadastral_parcel(lat: float, lon: float) -> dict[str, Any]:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Współrzędne poza zakresem.")

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
        raise RuntimeError("Nie udało się pobrać danych działki.") from last_error

    response.encoding = "utf-8"
    parcel = parse_cadastral_feature_info(response.text)
    if not parcel.get("parcel_id") and not parcel.get("parcel_number"):
        raise LookupError("Nie znaleziono działki w tym punkcie.")
    return parcel


@lru_cache(maxsize=512)
def _lookup_prg_address_cached(lat: float, lon: float) -> dict[str, Any]:
    response = map_downloads.get_http_session().get(
        config.PRG_ADDRESS_WFS_URL,
        params=prg_address_wfs_params(
            lat,
            lon,
            radius_m=config.PRG_ADDRESS_SEARCH_RADIUS_M,
            count=config.PRG_ADDRESS_MAX_FEATURES,
        ),
        timeout=config.PRG_ADDRESS_WFS_TIMEOUT,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return parse_prg_address_features(response.text, query_lat=lat, query_lon=lon)


@lru_cache(maxsize=512)
def _lookup_nominatim_address_cached(lat: float, lon: float) -> dict[str, Any]:
    response = map_downloads.get_http_session().get(
        config.NOMINATIM_REVERSE_URL,
        params={
            "format": "jsonv2",
            "lat": f"{lat:.8f}",
            "lon": f"{lon:.8f}",
            "addressdetails": "1",
            "zoom": "18",
            "accept-language": "pl",
        },
        headers={
            "User-Agent": config.NOMINATIM_USER_AGENT,
            "Accept": "application/json",
        },
        timeout=config.NOMINATIM_TIMEOUT,
    )
    response.raise_for_status()
    return normalize_reverse_geocode_result(response.json(), query_lat=lat, query_lon=lon)


def lookup_nearest_address(lat: float, lon: float) -> dict[str, Any]:
    lat, lon = validate_coordinates(lat, lon)
    rounded_lat = round(lat, 6)
    rounded_lon = round(lon, 6)
    try:
        return _lookup_prg_address_cached(rounded_lat, rounded_lon)
    except Exception:
        return _lookup_nominatim_address_cached(rounded_lat, rounded_lon)


def _query_coordinates(handler) -> tuple[float, float]:
    query = parse_qs(urlsplit(handler.path).query)
    return validate_coordinates((query.get("lat") or [""])[0], (query.get("lon") or [""])[0])


def handle_cadastral_identify(handler) -> None:
    if not access.require_public_layer(
        handler, "cadastral", "Warstwa dzialek jest teraz wylaczona dla niezalogowanych."
    ):
        return
    try:
        lat, lon = _query_coordinates(handler)
    except ValueError:
        http_responses.send_json(handler, 400, {"status": "error", "error": "Nieprawidłowe współrzędne."})
        return

    try:
        parcel = lookup_cadastral_parcel(lat, lon)
    except ValueError as exc:
        http_responses.send_json(handler, 400, {"status": "error", "error": str(exc)})
        return
    except LookupError as exc:
        http_responses.send_json(handler, 404, {"status": "not_found", "error": str(exc)})
        return
    except RuntimeError as exc:
        http_responses.send_internal_error(
            handler,
            502,
            "Cadastral upstream request failed",
            exc,
            public_error="Nie udało się pobrać danych działki.",
        )
        return
    http_responses.send_json(handler, 200, {"status": "ok", "parcel": parcel})


def handle_reverse_address(handler) -> None:
    try:
        lat, lon = _query_coordinates(handler)
    except ValueError:
        http_responses.send_json(handler, 400, {"status": "error", "error": "Nieprawidłowe współrzędne."})
        return

    try:
        address = lookup_nearest_address(lat, lon)
    except LookupError as exc:
        http_responses.send_json(handler, 404, {"status": "not_found", "error": str(exc)})
        return
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            502,
            "Reverse geocoding upstream request failed",
            exc,
            public_error="Nie udało się pobrać adresu.",
        )
        return
    http_responses.send_json(handler, 200, {"status": "ok", "address": address})

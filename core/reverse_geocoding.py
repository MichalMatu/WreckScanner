from __future__ import annotations

from typing import Any

from core.geo import meters_between


def _text(value: Any, max_len: int = 240) -> str:
    return str(value or "").replace("\x00", "").strip()[:max_len]


def _address_part(address: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(address.get(key))
        if value:
            return value
    return ""


def _result_distance_m(query_lat: float, query_lon: float, payload: dict[str, Any]) -> int | None:
    try:
        result_lat = float(payload.get("lat"))
        result_lon = float(payload.get("lon"))
    except (TypeError, ValueError):
        return None
    return int(round(meters_between(query_lat, query_lon, result_lat, result_lon)))


def normalize_reverse_geocode_result(payload: dict[str, Any], *, query_lat: float, query_lon: float) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LookupError("Nie znaleziono adresu w tym punkcie.")

    address = payload.get("address") if isinstance(payload.get("address"), dict) else {}
    road = _address_part(address, "road", "pedestrian", "footway", "path", "cycleway")
    house_number = _address_part(address, "house_number")
    city = _address_part(address, "city", "town", "village", "municipality")
    district = _address_part(address, "suburb", "city_district", "neighbourhood", "quarter")
    postcode = _address_part(address, "postcode")
    display_name = _text(payload.get("display_name"), max_len=500)

    primary = " ".join(part for part in (road, house_number) if part)
    if not primary:
        primary = _address_part(address, "amenity", "building", "shop", "tourism") or display_name
    if not primary:
        raise LookupError("Nie znaleziono adresu w tym punkcie.")

    locality = ", ".join(part for part in (postcode, city) if part)
    formatted = ", ".join(part for part in (primary, locality) if part)

    return {
        "formatted": formatted or primary,
        "display_name": display_name,
        "road": road,
        "house_number": house_number,
        "postcode": postcode,
        "city": city,
        "district": district,
        "lat": _text(payload.get("lat"), max_len=40),
        "lon": _text(payload.get("lon"), max_len=40),
        "distance_m": _result_distance_m(query_lat, query_lon, payload),
        "source": "nominatim",
    }

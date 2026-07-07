from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Any

GRS80_A = 6_378_137.0
GRS80_F = 1 / 298.257222101
PUWG92_LON_0 = math.radians(19.0)
PUWG92_K_0 = 0.9993
PUWG92_FALSE_EASTING = 500_000.0
PUWG92_FALSE_NORTHING = -5_300_000.0


def _text(value: Any, max_len: int = 240) -> str:
    return str(value or "").replace("\x00", "").strip()[:max_len]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def wgs84_to_puwg1992(lat: float, lon: float) -> tuple[float, float]:
    e2 = GRS80_F * (2 - GRS80_F)
    ep2 = e2 / (1 - e2)
    phi = math.radians(lat)
    lam = math.radians(lon)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)
    n_radius = GRS80_A / math.sqrt(1 - e2 * sin_phi * sin_phi)
    t = tan_phi * tan_phi
    c = ep2 * cos_phi * cos_phi
    a = (lam - PUWG92_LON_0) * cos_phi
    e4 = e2 * e2
    e6 = e4 * e2
    meridian_arc = GRS80_A * (
        (1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
        - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
        + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
        - (35 * e6 / 3072) * math.sin(6 * phi)
    )
    easting = PUWG92_FALSE_EASTING + PUWG92_K_0 * n_radius * (
        a + (1 - t + c) * a**3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * a**5 / 120
    )
    northing = PUWG92_FALSE_NORTHING + PUWG92_K_0 * (
        meridian_arc
        + n_radius
        * tan_phi
        * (
            a * a / 2
            + (5 - t + 9 * c + 4 * c * c) * a**4 / 24
            + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * a**6 / 720
        )
    )
    return easting, northing


def prg_address_wfs_params(lat: float, lon: float, *, radius_m: float, count: int) -> dict[str, str]:
    easting, northing = wgs84_to_puwg1992(lat, lon)
    # This MapServer WFS exposes EPSG:2180 in northing/easting axis order.
    x = northing
    y = easting
    return {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": "ms:prg-adresy",
        "SRSNAME": "EPSG:2180",
        "BBOX": f"{x - radius_m:.3f},{y - radius_m:.3f},{x + radius_m:.3f},{y + radius_m:.3f},EPSG:2180",
        "COUNT": str(count),
    }


def _child_text(feature: ET.Element, name: str) -> str:
    for child in feature.iter():
        if _local_name(child.tag) == name:
            return _text(child.text)
    return ""


def _feature_position(feature: ET.Element) -> tuple[float, float] | None:
    for child in feature.iter():
        if _local_name(child.tag) != "pos":
            continue
        parts = _text(child.text).split()
        if len(parts) < 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None
    return None


def _address_from_feature(feature: ET.Element, *, query_x: float, query_y: float) -> dict[str, Any] | None:
    road = _child_text(feature, "ulica")
    house_number = _child_text(feature, "numer")
    city = _child_text(feature, "miejscowosc")
    postcode = _child_text(feature, "kod")
    position = _feature_position(feature)
    if not road and not city:
        return None
    distance_m = None
    projected_x = ""
    projected_y = ""
    if position:
        projected_x = f"{position[0]:.3f}"
        projected_y = f"{position[1]:.3f}"
        distance_m = int(round(math.hypot(position[0] - query_x, position[1] - query_y)))
    primary = " ".join(part for part in (road, house_number) if part) or city
    locality = ", ".join(part for part in (postcode, city) if part)
    formatted = ", ".join(part for part in (primary, locality) if part)
    return {
        "formatted": formatted,
        "display_name": formatted,
        "road": road,
        "house_number": house_number,
        "postcode": postcode,
        "city": city,
        "district": "",
        "lat": "",
        "lon": "",
        "projected_x": projected_x,
        "projected_y": projected_y,
        "distance_m": distance_m,
        "source": "prg",
        "source_label": "PRG/GUGiK",
    }


def parse_prg_address_features(xml_text: str, *, query_lat: float, query_lon: float) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise LookupError("Nie udało się odczytać odpowiedzi PRG/GUGiK.") from exc

    easting, northing = wgs84_to_puwg1992(query_lat, query_lon)
    query_x = northing
    query_y = easting
    addresses = []
    for feature in root.iter():
        if _local_name(feature.tag) != "prg-adresy":
            continue
        address = _address_from_feature(feature, query_x=query_x, query_y=query_y)
        if address:
            addresses.append(address)

    if not addresses:
        raise LookupError("Nie znaleziono punktu adresowego PRG/GUGiK w pobliżu.")
    return min(addresses, key=lambda item: float(item["distance_m"] if item["distance_m"] is not None else 1_000_000))

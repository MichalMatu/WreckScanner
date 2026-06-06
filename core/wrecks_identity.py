from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from core.geo import external_map_links


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def wreck_id(lat: float, lon: float) -> str:
    return f"wreck_{int(round(lat * 1_000_000))}_{int(round(lon * 1_000_000))}"


def validate_coordinates(lat: Any, lon: Any) -> tuple[float, float]:
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError) as exc:
        raise ValueError("Podaj prawidłowe współrzędne pojazdu.") from exc
    if not math.isfinite(lat_f) or not math.isfinite(lon_f):
        raise ValueError("Podaj prawidłowe współrzędne pojazdu.")
    if not -90 <= lat_f <= 90 or not -180 <= lon_f <= 180:
        raise ValueError("Współrzędne pojazdu są poza dozwolonym zakresem.")
    return lat_f, lon_f


def links(lat: float, lon: float) -> dict[str, str]:
    return external_map_links(lat, lon)

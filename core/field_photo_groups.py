from __future__ import annotations

import math
from typing import Any

from core import config
from core.field_photo_metadata import issue_type
from core.geo import meters_between


def field_photo_coordinates(record: dict[str, Any]) -> tuple[float, float] | None:
    try:
        lat = float(record.get("lat"))
        lon = float(record.get("lon"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lon):
        return None
    return lat, lon


def is_vehicle_record(record: dict[str, Any]) -> bool:
    try:
        return issue_type(record.get("issue_type")) == config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE
    except ValueError:
        return False


def same_vehicle_photo_group(
    anchor: dict[str, Any],
    candidate: dict[str, Any],
    *,
    radius_m: float = config.FIELD_PHOTO_GROUP_RADIUS_M,
) -> bool:
    if not is_vehicle_record(anchor) or not is_vehicle_record(candidate):
        return False
    anchor_coords = field_photo_coordinates(anchor)
    candidate_coords = field_photo_coordinates(candidate)
    if not anchor_coords or not candidate_coords:
        return False
    return meters_between(anchor_coords[0], anchor_coords[1], candidate_coords[0], candidate_coords[1]) <= radius_m


def vehicle_photo_group_records(
    records: list[dict[str, Any]],
    anchor: dict[str, Any],
    *,
    radius_m: float = config.FIELD_PHOTO_GROUP_RADIUS_M,
) -> list[dict[str, Any]]:
    return [record for record in records if same_vehicle_photo_group(anchor, record, radius_m=radius_m)]

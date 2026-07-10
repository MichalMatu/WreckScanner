from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.field_photo_groups import vehicle_photo_group_records


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def set_vehicle_resolution(record: dict[str, Any], status: str, updated_at: str | None) -> None:
    record["vehicle_resolution_status"] = status
    record["vehicle_resolution_updated_at"] = updated_at


def apply_vehicle_resolution_group_update(
    records: list[dict[str, Any]],
    anchor_record: dict[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    updated_at = _now_iso()
    updated_records = vehicle_photo_group_records(records, anchor_record)
    for record in updated_records:
        set_vehicle_resolution(record, status, updated_at)
    return updated_records

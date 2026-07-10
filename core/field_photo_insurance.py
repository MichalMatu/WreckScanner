from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core import config
from core.field_photo_groups import vehicle_photo_group_records


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def vehicle_insurance_checked_at_for_status(status: str) -> str | None:
    return None if status == config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS else _now_iso()


def set_vehicle_insurance(record: dict[str, Any], status: str, checked_at: str | None) -> None:
    record["vehicle_insurance_status"] = status
    record["vehicle_insurance_checked_at"] = checked_at


def apply_vehicle_insurance_group_update(
    records: list[dict[str, Any]],
    anchor_record: dict[str, Any],
    status: str,
) -> list[dict[str, Any]]:
    checked_at = vehicle_insurance_checked_at_for_status(status)
    updated_records = vehicle_photo_group_records(records, anchor_record)
    for record in updated_records:
        set_vehicle_insurance(record, status, checked_at)
    return updated_records

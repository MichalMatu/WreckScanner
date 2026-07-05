from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config
from core.field_photo_groups import vehicle_photo_group_records
from core.field_photo_store import list_field_records, save_field_record


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def vehicle_insurance_checked_at_for_status(status: str) -> str | None:
    return None if status == config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS else _now_iso()


def set_vehicle_insurance(record: dict[str, Any], status: str, checked_at: str | None) -> None:
    record["vehicle_insurance_status"] = status
    record["vehicle_insurance_checked_at"] = checked_at


def records_with_anchor_snapshot(storage_dir: Path, anchor_record: dict[str, Any]) -> list[dict[str, Any]]:
    anchor_id = str(anchor_record.get("id") or "")
    records: list[dict[str, Any]] = []
    anchor_seen = False
    for record in list_field_records(storage_dir):
        if str(record.get("id") or "") == anchor_id:
            records.append(anchor_record)
            anchor_seen = True
        else:
            records.append(record)
    if not anchor_seen:
        records.append(anchor_record)
    return records


def save_vehicle_insurance_group_update(
    storage_dir: Path,
    anchor_record: dict[str, Any],
    status: str,
) -> list[str]:
    updated_ids: list[str] = []
    checked_at = vehicle_insurance_checked_at_for_status(status)
    records = records_with_anchor_snapshot(storage_dir, anchor_record)
    for record in vehicle_photo_group_records(records, anchor_record):
        set_vehicle_insurance(record, status, checked_at)
        save_field_record(storage_dir, record)
        updated_ids.append(str(record["id"]))
    return updated_ids

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.field_photo_groups import vehicle_photo_group_records
from core.field_photo_store import list_field_records, save_field_record


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def set_vehicle_resolution(record: dict[str, Any], status: str, updated_at: str | None) -> None:
    record["vehicle_resolution_status"] = status
    record["vehicle_resolution_updated_at"] = updated_at


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


def save_vehicle_resolution_group_update(
    storage_dir: Path,
    anchor_record: dict[str, Any],
    status: str,
) -> list[str]:
    updated_ids: list[str] = []
    updated_at = _now_iso()
    records = records_with_anchor_snapshot(storage_dir, anchor_record)
    for record in vehicle_photo_group_records(records, anchor_record):
        set_vehicle_resolution(record, status, updated_at)
        save_field_record(storage_dir, record)
        updated_ids.append(str(record["id"]))
    return updated_ids

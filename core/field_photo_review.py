from __future__ import annotations

from pathlib import Path
from typing import Any

from core import config
from core.field_photo_insurance import save_vehicle_insurance_group_update
from core.field_photo_metadata import (
    validated_vehicle_insurance_update,
    validated_vehicle_resolution_update,
)
from core.field_photo_resolution import save_vehicle_resolution_group_update
from core.field_photo_serialization import field_photo_summary
from core.field_photo_store import save_field_record
from core.photo_privacy import apply_review_update, is_approved


def review_field_photo_record(
    record: dict[str, Any],
    record_dir: Path,
    storage_dir: Path,
    private_root: Path,
    *,
    status: Any = None,
    redactions: Any = None,
    vehicle_insurance_status: Any = None,
    vehicle_resolution_status: Any = None,
) -> dict[str, Any]:
    validated_vehicle_insurance_status = validated_vehicle_insurance_update(record, vehicle_insurance_status)
    validated_vehicle_resolution_status = validated_vehicle_resolution_update(record, vehicle_resolution_status)
    review_updated = status is not None
    if (
        not review_updated
        and validated_vehicle_insurance_status is None
        and validated_vehicle_resolution_status is None
    ):
        raise ValueError("Brak decyzji do zapisania.")
    if review_updated:
        apply_review_update(
            record,
            record_dir,
            private_root,
            status=status,
            redactions=record.get("redactions") if redactions is None else redactions,
            thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
            thumb_quality=config.FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY,
        )

    insurance_updated_ids = []
    if validated_vehicle_insurance_status is not None:
        insurance_updated_ids = save_vehicle_insurance_group_update(
            storage_dir,
            record,
            validated_vehicle_insurance_status,
        )
    resolution_updated_ids = []
    if validated_vehicle_resolution_status is not None:
        resolution_updated_ids = save_vehicle_resolution_group_update(
            storage_dir,
            record,
            validated_vehicle_resolution_status,
        )
    if not insurance_updated_ids and not resolution_updated_ids:
        save_field_record(storage_dir, record)

    result = {"status": "ok", "photo": field_photo_summary(record) if is_approved(record) else {"id": record["id"]}}
    if validated_vehicle_insurance_status is not None:
        result["vehicle_insurance_updated_photo_ids"] = insurance_updated_ids
    if validated_vehicle_resolution_status is not None:
        result["vehicle_resolution_updated_photo_ids"] = resolution_updated_ids
    return result

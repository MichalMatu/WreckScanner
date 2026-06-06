from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.photo_privacy import ensure_review_fields, is_approved
from core.wrecks_photos import migrate_attached_photo


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def migrate_wreck_record(record_dir: Path, record: dict[str, Any]) -> bool:
    changed = False
    if "public_review_status" not in record:
        record["public_review_status"] = "approved"
        changed = True
    changed = ensure_review_fields(record) or changed
    if "submission_owner" not in record:
        record["submission_owner"] = None
        changed = True
    if is_approved(record) and record.get("reviewed_at") is None:
        record["reviewed_at"] = record.get("created_at") or _now_iso()
        changed = True
    attached = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    for photo in attached:
        if isinstance(photo, dict):
            changed = migrate_attached_photo(record_dir, record, photo) or changed
    if attached and record.get("attached_photos") is not attached:
        record["attached_photos"] = attached
        changed = True
    return changed

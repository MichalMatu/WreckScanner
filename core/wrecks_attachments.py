from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from core import config
from core.photo_privacy import safe_child
from core.uploads import UploadedFile
from core.wreck_photo_transfers import copy_field_photo_to_wreck, prepare_field_photo_copy
from core.wrecks_identity import now_iso
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_photos import (
    attached_photo_by_id,
    generate_wreck_public_derivatives,
    migrate_attached_photo,
    photo_dir,
    remove_wreck_public_derivatives,
    save_attached_photo,
)
from core.wrecks_public import wreck_summary
from core.wrecks_rendering import render_record_html
from core.wrecks_review import apply_wreck_photo_review
from core.wrecks_store import read_json, record_dir_for, write_json


def _render_record_html(record: dict[str, Any], record_dir: Path) -> None:
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    render_record_html(record, record_dir)


def review_wreck_photo(
    wreck_id: str,
    photo_id: str,
    wrecks_dir: Path,
    *,
    status: Any,
    redactions: Any,
) -> dict[str, Any]:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    migrate_wreck_record(record_dir, record)
    photo = attached_photo_by_id(record, photo_id)
    status_text = apply_wreck_photo_review(photo, status=status, redactions=redactions)
    if status_text == "approved":
        generate_wreck_public_derivatives(photo, record_dir)
    else:
        remove_wreck_public_derivatives(photo, record_dir)
    write_json(photo_dir(record_dir, photo_id) / "record.json", photo)
    record["updated_at"] = now_iso()
    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)
    return {"status": "ok", "photo": photo, "wreck": wreck_summary(record)}


def delete_wreck_photo(wreck_id: str, photo_id: str, wrecks_dir: Path) -> dict[str, Any]:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    migrate_wreck_record(record_dir, record)
    photo = attached_photo_by_id(record, photo_id)
    private_original = safe_child(config.PRIVATE_PHOTOS_DIR, photo.get("private_original_file"))
    remove_wreck_public_derivatives(photo, record_dir)
    if private_original.exists():
        private_original.unlink()
    photo_record_dir = photo_dir(record_dir, photo_id)
    if photo_record_dir.exists():
        shutil.rmtree(photo_record_dir)
    record["attached_photos"] = [
        item
        for item in (record.get("attached_photos") or [])
        if not (isinstance(item, dict) and str(item.get("id") or "") == photo_id)
    ]
    record["updated_at"] = now_iso()
    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)
    return {"status": "ok", "deleted": photo_id, "wreck": wreck_summary(record)}


def attach_field_photos_to_wreck(
    wreck_id: str,
    photo_ids: list[Any],
    field_photos_dir: Path,
    wrecks_dir: Path,
) -> dict[str, Any]:
    if not photo_ids:
        raise ValueError("Wybierz co najmniej jedno zdjęcie terenowe.")
    unique_photo_ids = list(dict.fromkeys(str(photo_id or "").strip() for photo_id in photo_ids))
    if len(unique_photo_ids) > config.MAX_WRECK_PHOTOS_PER_UPLOAD:
        raise ValueError(f"Możesz dodać maksymalnie {config.MAX_WRECK_PHOTOS_PER_UPLOAD} zdjęć naraz.")

    wreck_record_dir = record_dir_for(wreck_id, wrecks_dir)
    wreck_record = read_json(wreck_record_dir / "record.json")
    if not isinstance(wreck_record, dict):
        raise ValueError("Nieprawidłowy format record.json.")

    field_records: list[dict[str, Any]] = []
    for photo_id in unique_photo_ids:
        field_records.append(prepare_field_photo_copy(photo_id, field_photos_dir))

    attached = wreck_record.get("attached_photos")
    if not isinstance(attached, list):
        attached = []
    moved = []
    attached_ids = {str(photo.get("id") or "") for photo in attached if isinstance(photo, dict)}
    for field_record in field_records:
        photo_id = str(field_record.get("id") or "")
        if photo_id in attached_ids:
            continue
        copied_photo = copy_field_photo_to_wreck(field_record, wreck_record_dir)
        migrate_attached_photo(wreck_record_dir, wreck_record, copied_photo)
        moved.append(copied_photo)
        attached.append(copied_photo)
        attached_ids.add(photo_id)
        wreck_record["attached_photos"] = attached
        wreck_record["updated_at"] = now_iso()
        write_json(wreck_record_dir / "record.json", wreck_record)
    _render_record_html(wreck_record, wreck_record_dir)
    return {
        "status": "ok",
        "wreck_id": wreck_id,
        "photos": moved,
        "attached_count": len(moved),
        "photo_count": len(attached),
        "copied_field_photo_ids": [photo["id"] for photo in moved],
        "wreck": wreck_summary(wreck_record),
    }


def attach_wreck_photos(wreck_id: str, uploads: list[UploadedFile], wrecks_dir: Path) -> dict[str, Any]:
    photo_uploads = [upload for upload in uploads if upload.filename or upload.data]
    if not photo_uploads:
        raise ValueError("Wybierz co najmniej jedno zdjęcie.")
    if len(photo_uploads) > config.MAX_WRECK_PHOTOS_PER_UPLOAD:
        raise ValueError(f"Możesz dodać maksymalnie {config.MAX_WRECK_PHOTOS_PER_UPLOAD} zdjęć naraz.")

    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")

    attached = record.get("attached_photos")
    if not isinstance(attached, list):
        attached = []
    saved = [save_attached_photo(upload, record_dir) for upload in photo_uploads]
    attached.extend(saved)
    record["attached_photos"] = attached
    record["updated_at"] = now_iso()
    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)
    return {"status": "ok", "photos": saved, "photo_count": len(attached), "wreck": wreck_summary(record)}

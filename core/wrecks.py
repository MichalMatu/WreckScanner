from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from core.photo_privacy import is_approved
from core.wrecks_catalog import load_records as _load_records
from core.wrecks_identity import now_iso as _now_iso
from core.wrecks_migration import migrate_wreck_record as _migrate_wreck_record
from core.wrecks_public import wreck_summary
from core.wrecks_rendering import approved_attached_photos, render_record_html
from core.wrecks_review import apply_wreck_review
from core.wrecks_review import wreck_photo_review_items as _wreck_photo_review_items
from core.wrecks_review import wreck_review_items as _wreck_review_items
from core.wrecks_store import read_json, record_dir_for, validate_wreck_id, write_json


def _has_vehicle_photos(record: dict[str, Any], *, include_pending: bool) -> bool:
    photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    if include_pending:
        return bool(photos)
    return bool(approved_attached_photos(record))


def list_wrecks(wrecks_dir: Path, *, include_pending: bool = False) -> list[dict[str, Any]]:
    return [
        wreck_summary(record)
        for record in _load_records(wrecks_dir)
        if (include_pending or is_approved(record)) and _has_vehicle_photos(record, include_pending=include_pending)
    ]


def list_wreck_review_items(wrecks_dir: Path, *, status: str = "pending") -> list[dict[str, Any]]:
    return _wreck_review_items(_load_records(wrecks_dir), status=status)


def review_wreck(
    wreck_id: str,
    wrecks_dir: Path,
    *,
    status: Any,
) -> dict[str, Any]:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    _migrate_wreck_record(record_dir, record)
    apply_wreck_review(record, status=status, updated_at=_now_iso())
    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)
    return {"status": "ok", "wreck": wreck_summary(record)}


def list_wreck_photo_review_items(wrecks_dir: Path) -> list[dict[str, Any]]:
    return _wreck_photo_review_items(_load_records(wrecks_dir))


def delete_wreck(wreck_id: str, wrecks_dir: Path) -> dict[str, Any]:
    wreck_id = validate_wreck_id(wreck_id)
    root = wrecks_dir.resolve()
    record_dir = (wrecks_dir / wreck_id).resolve()
    if root != record_dir and root not in record_dir.parents:
        raise ValueError("Nieprawidłowa ścieżka sprawy pojazdu.")
    if not record_dir.exists():
        raise FileNotFoundError("Nie znaleziono zapisanej sprawy pojazdu.")
    if not (record_dir / "record.json").exists():
        raise ValueError("Katalog nie wygląda jak sprawa pojazdu.")
    shutil.rmtree(record_dir)
    return {"status": "ok", "deleted": wreck_id}


def _render_record_html(record: dict[str, Any], record_dir: Path) -> None:
    if _migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    render_record_html(record, record_dir)


def render_wreck_record_html(record: dict[str, Any], record_dir: Path) -> None:
    _render_record_html(record, record_dir)


def refresh_wreck_report(wreck_id: str, wrecks_dir: Path) -> Path:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    _render_record_html(record, record_dir)
    return record_dir / "index.html"

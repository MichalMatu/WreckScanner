from __future__ import annotations

import json
from pathlib import Path

from core import config
from core.photo_privacy import is_approved, safe_child
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_photos import attached_photo_by_id
from core.wrecks_rendering import approved_attached_photos
from core.wrecks_store import read_json, record_dir_for, write_json


def wreck_is_public(wreck_id: str, wrecks_dir: Path) -> bool:
    try:
        record_dir = record_dir_for(wreck_id, wrecks_dir)
        record = read_json(record_dir / "record.json")
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        return False
    if not isinstance(record, dict):
        return False
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    return is_approved(record)


def wreck_photo_original_asset(wreck_id: str, photo_id: str, wrecks_dir: Path) -> tuple[Path, str]:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    photo = attached_photo_by_id(record, photo_id)
    path = safe_child(config.PRIVATE_PHOTOS_DIR, photo.get("private_original_file"))
    if not path.exists():
        raise FileNotFoundError("Nie znaleziono prywatnego oryginału zdjęcia.")
    return path, str(photo.get("content_type") or "application/octet-stream")


def public_wreck_asset(wreck_id: str, relative_path: str, wrecks_dir: Path) -> tuple[Path, str]:
    record_dir = record_dir_for(wreck_id, wrecks_dir)
    rel = str(relative_path or "").replace("\\", "/").strip("/")
    if not rel or rel.startswith("/") or any(part in {"", ".", ".."} for part in rel.split("/")):
        raise FileNotFoundError("Nie znaleziono publicznego pliku sprawy pojazdu.")

    record = read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)

    suffix = Path(rel).suffix.lower()
    if rel.startswith("evidence/") and suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        path = safe_child(record_dir, rel)
        if not path.exists():
            raise FileNotFoundError("Nie znaleziono publicznego pliku sprawy pojazdu.")
        return path, "image/jpeg" if suffix in {".jpg", ".jpeg"} else f"image/{suffix.removeprefix('.')}"

    if rel.startswith("photos/"):
        for photo in approved_attached_photos(record):
            if rel in {str(photo.get("public_image_file") or ""), str(photo.get("public_thumb_file") or "")}:
                path = safe_child(record_dir, rel)
                if not path.exists():
                    raise FileNotFoundError("Nie znaleziono publicznego pliku sprawy pojazdu.")
                return path, "image/jpeg"

    raise FileNotFoundError("Nie znaleziono publicznego pliku sprawy pojazdu.")

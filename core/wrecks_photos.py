from __future__ import annotations

import hashlib
import io
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from core import config
from core.photo_privacy import (
    ensure_review_fields,
    generate_public_derivatives,
    is_approved,
    migrate_private_original,
    safe_child,
    safe_existing_child,
)
from core.uploads import UploadedFile
from core.wrecks_store import write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _private_original_rel(wreck_id: str, photo_id: str, ext: str) -> str:
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"wreck_photos/{wreck_id}/{photo_id}/original{ext.lower()}"


def _safe_original_name(raw_name: str, ext: str) -> str:
    stem = Path(raw_name or "").stem or "zdjecie"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "zdjecie"
    return f"{stem[:80]}{ext}"


def photo_dir(record_dir: Path, photo_id: str) -> Path:
    return record_dir / "photos" / photo_id


def generate_wreck_public_derivatives(photo: dict[str, Any], record_dir: Path) -> None:
    photo_id = str(photo.get("id") or "")
    if not photo_id:
        raise ValueError("Nieprawidłowy identyfikator zdjęcia.")
    photo_record_dir = photo_dir(record_dir, photo_id)
    local_photo = dict(photo)
    public_image_rel = str(photo.get("public_image_file") or "")
    public_thumb_rel = str(photo.get("public_thumb_file") or "")
    if public_image_rel.startswith(f"photos/{photo_id}/"):
        local_photo["public_image_file"] = Path(public_image_rel).name
    if public_thumb_rel.startswith(f"photos/{photo_id}/"):
        local_photo["public_thumb_file"] = Path(public_thumb_rel).name
    generate_public_derivatives(
        local_photo,
        photo_record_dir,
        config.PRIVATE_PHOTOS_DIR,
        thumb_max_edge=config.WRECK_PHOTO_THUMB_MAX_EDGE_PX,
        thumb_quality=config.WRECK_PHOTO_THUMB_QUALITY,
    )
    photo["public_image_file"] = f"photos/{photo_id}/{local_photo['public_image_file']}"
    photo["public_thumb_file"] = f"photos/{photo_id}/{local_photo['public_thumb_file']}"
    photo["public_width"] = local_photo.get("public_width")
    photo["public_height"] = local_photo.get("public_height")


def remove_wreck_public_derivatives(photo: dict[str, Any], record_dir: Path) -> None:
    for key in ("public_image_file", "public_thumb_file"):
        path = safe_existing_child(record_dir, photo.get(key))
        if path:
            path.unlink()
    for key in ("public_image_file", "public_thumb_file", "public_width", "public_height"):
        photo.pop(key, None)


def migrate_attached_photo(record_dir: Path, record: dict[str, Any], photo: dict[str, Any]) -> bool:
    changed = ensure_review_fields(photo)
    wreck_id = str(record.get("id") or record_dir.name)
    photo_id = str(photo.get("id") or "")
    if not photo_id:
        return changed
    photo_record_dir = photo_dir(record_dir, photo_id)
    photo_record_dir.mkdir(parents=True, exist_ok=True)
    changed = (
        migrate_private_original(
            photo,
            record_dir,
            config.PRIVATE_PHOTOS_DIR,
            scope="wreck_photos",
            photo_id=photo_id,
            owner_id=wreck_id,
        )
        or changed
    )
    for legacy_key in ("thumb_file", "thumbnail_file", "original_url", "original_path"):
        if legacy_key in photo:
            photo.pop(legacy_key, None)
            changed = True
    if not is_approved(photo):
        remove_wreck_public_derivatives(photo, record_dir)
    elif not safe_existing_child(record_dir, photo.get("public_image_file")) or not safe_existing_child(
        record_dir, photo.get("public_thumb_file")
    ):
        generate_wreck_public_derivatives(photo, record_dir)
        changed = True
    write_json(photo_record_dir / "record.json", photo)
    return changed


def attached_photo_by_id(record: dict[str, Any], photo_id: str) -> dict[str, Any]:
    for photo in record.get("attached_photos") or []:
        if isinstance(photo, dict) and str(photo.get("id") or "") == photo_id:
            return photo
    raise FileNotFoundError("Nie znaleziono zdjęcia w sprawie pojazdu.")


def _wreck_photo_id(upload: UploadedFile) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(
        f"{upload.filename}:{len(upload.data)}:{secrets.token_urlsafe(12)}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:8]
    return f"photo_{stamp}_{digest}"


def save_attached_photo(
    upload: UploadedFile, record_dir: Path, *, submission_owner: str | None = None
) -> dict[str, Any]:
    if upload.field_name not in {"photos", "photos[]", "photo"}:
        raise ValueError("Nie znaleziono pola pliku 'photos[]'.")
    size = len(upload.data)
    if size <= 0:
        raise ValueError("Dodaj zdjęcie do uploadu.")
    if size > config.MAX_WRECK_PHOTO_BYTES:
        raise ValueError("Zdjęcie przekracza limit 10 MB.")
    try:
        with Image.open(io.BytesIO(upload.data)) as image:
            image_format = str(image.format or "").upper()
            if image_format not in config.ALLOWED_UPLOAD_IMAGE_FORMATS:
                raise ValueError("Dozwolone są tylko zdjęcia JPG, PNG albo WebP.")
            width, height = image.size
    except UnidentifiedImageError as exc:
        raise ValueError("Plik nie jest obsługiwanym zdjęciem.") from exc

    ext, content_type = config.ALLOWED_UPLOAD_IMAGE_FORMATS[image_format]
    photo_id = _wreck_photo_id(upload)
    photo_record_dir = photo_dir(record_dir, photo_id)
    photo_record_dir.mkdir(parents=True, exist_ok=False)
    private_original_file = _private_original_rel(record_dir.name, photo_id, ext)
    original_path = safe_child(config.PRIVATE_PHOTOS_DIR, private_original_file)
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(upload.data)
    photo = {
        "id": photo_id,
        "created_at": _now_iso(),
        "original_filename": _safe_original_name(upload.filename, ext),
        "content_type": content_type,
        "format": image_format,
        "size_bytes": size,
        "image_width": width,
        "image_height": height,
        "private_original_file": private_original_file,
        "public_review_status": "pending",
        "redactions": [],
        "reviewed_at": None,
        "submission_owner": submission_owner,
    }
    write_json(photo_record_dir / "record.json", photo)
    return photo

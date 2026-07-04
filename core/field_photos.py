from __future__ import annotations

import hashlib
import io
import math
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from PIL import Image, UnidentifiedImageError

from core import config
from core.field_photo_store import (
    FIELD_PHOTO_ID_RE as _FIELD_PHOTO_ID_RE,
)
from core.field_photo_store import (
    delete_field_record as _delete_field_record,
)
from core.field_photo_store import (
    list_field_records as _list_field_records,
)
from core.field_photo_store import (
    load_field_record_by_id as _load_field_record_by_id,
)
from core.field_photo_store import (
    save_field_record as _save_field_record,
)
from core.field_photo_store import (
    validate_photo_id as _validate_photo_id,
)
from core.geo import external_map_links
from core.photo_privacy import (
    REVIEW_STATUSES,
    apply_review_update,
    ensure_review_fields,
    generate_public_derivatives,
    is_approved,
    remove_empty_private_photo_dir,
    remove_public_derivatives,
    review_status,
    safe_child,
    safe_existing_child,
)
from core.photo_tokens import new_photo_edit_token_hash, normalize_photo_edit_token, verify_photo_edit_token
from core.uploads import UploadedFile

FIELD_PHOTO_ID_RE = _FIELD_PHOTO_ID_RE


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _now_iso() -> str:
    return _now_utc().isoformat().replace("+00:00", "Z")


def _safe_text(value: Any, max_len: int = 300) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:max_len]


def _safe_original_name(raw_name: str, ext: str) -> str:
    stem = Path(raw_name or "").stem or "zdjecie"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "zdjecie"
    return f"{stem[:80]}{ext}"


def _record_dir_for(photo_id: str, storage_dir: Path) -> Path:
    photo_id = _validate_photo_id(photo_id)
    root = storage_dir.resolve()
    record_dir = (storage_dir / photo_id).resolve()
    if root != record_dir and root not in record_dir.parents:
        raise ValueError("Nieprawidłowa ścieżka zdjęcia.")
    return record_dir


def _format_exif_datetime(value: Any) -> str | None:
    text = _safe_text(value, 80)
    match = re.fullmatch(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", text)
    if not match:
        return text or None
    year, month, day, hour, minute, second = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}"


def _limited_exif(exif: Image.Exif) -> dict[str, str]:
    labels = {
        271: "make",
        272: "model",
        306: "datetime",
        36867: "datetime_original",
        36868: "datetime_digitized",
    }
    values: dict[str, str] = {}
    for tag, label in labels.items():
        value = _safe_text(exif.get(tag), 200)
        if value:
            values[label] = value
    return values


def _captured_at(exif: Image.Exif) -> str | None:
    return _format_exif_datetime(exif.get(36867) or exif.get(306))


def _coord_float(value: Any, label: str) -> float:
    try:
        coord = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nieprawidłowa wartość {label}.") from exc
    if not math.isfinite(coord):
        raise ValueError(f"Nieprawidłowa wartość {label}.")
    return coord


def _map_coordinates_from(map_lat: Any = None, map_lon: Any = None) -> tuple[float, float, Literal["map"]]:
    if map_lat is None or map_lon is None or str(map_lat).strip() == "" or str(map_lon).strip() == "":
        raise ValueError("Wskaż punkt zdjęcia na mapie i spróbuj ponownie.")
    lat = _coord_float(map_lat, "map_lat")
    lon = _coord_float(map_lon, "map_lon")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Nieprawidłowe współrzędne punktu mapy.")
    return lat, lon, "map"


def _validated_lat_lon(lat_value: Any, lon_value: Any) -> tuple[float, float]:
    lat = _coord_float(lat_value, "lat")
    lon = _coord_float(lon_value, "lon")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Nieprawidłowe współrzędne zdjęcia terenowego.")
    return lat, lon


def _issue_type(value: Any) -> str:
    issue_type = str(value or config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE).strip()
    if issue_type not in config.FIELD_PHOTO_ISSUE_TYPES:
        raise ValueError("Nieprawidłowy typ pinezki terenowej.")
    return issue_type


def _links(lat: float, lon: float) -> dict[str, str]:
    return external_map_links(lat, lon)


def _photo_id(upload: UploadedFile) -> str:
    stamp = _now_utc().strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(
        f"{upload.filename}:{len(upload.data)}:{secrets.token_urlsafe(12)}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:8]
    return f"photo_{stamp}_{digest}"


def _private_dir(private_dir: Path | None) -> Path:
    return private_dir or config.PRIVATE_PHOTOS_DIR


def _prepare_field_record(record_dir: Path, record: dict[str, Any], private_dir: Path) -> bool:
    changed = ensure_review_fields(record)
    if not is_approved(record):
        remove_public_derivatives(record, record_dir)
    elif not safe_existing_child(record_dir, record.get("public_image_file")) or not safe_existing_child(
        record_dir, record.get("public_thumb_file")
    ):
        generate_public_derivatives(
            record,
            record_dir,
            private_dir,
            thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
            thumb_quality=config.FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY,
        )
        changed = True
    return changed


def _load_field_record(record_dir: Path, private_dir: Path) -> dict[str, Any]:
    record = _load_field_record_by_id(record_dir.name, record_dir.parent)
    if _prepare_field_record(record_dir, record, private_dir):
        _save_field_record(record_dir.parent, record)
    return record


def _public_file_url(photo_id: str, asset: Literal["public-image", "public-thumb"]) -> str:
    return f"/api/field-photos/{photo_id}/{asset}"


def field_photo_record_dir(photo_id: str, storage_dir: Path) -> Path:
    return _record_dir_for(photo_id, storage_dir)


def load_field_photo_record(
    photo_id: str,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    return _load_field_record(record_dir, _private_dir(private_dir))


def list_field_photo_records(
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
    prepare: bool = True,
) -> list[dict[str, Any]]:
    private_root = _private_dir(private_dir)
    records: list[dict[str, Any]] = []
    for record in _list_field_records(storage_dir):
        record_dir = _record_dir_for(str(record["id"]), storage_dir)
        if prepare and _prepare_field_record(record_dir, record, private_root):
            _save_field_record(storage_dir, record)
        records.append(record)
    return records


def save_field_photo_record(record: dict[str, Any], storage_dir: Path) -> None:
    _save_field_record(storage_dir, record)


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    photo_id = str(record["id"])
    summary = {
        "id": photo_id,
        "created_at": record.get("created_at"),
        "submitted_at": record.get("submitted_at"),
        "format": record.get("format"),
        "public_width": record.get("public_width"),
        "public_height": record.get("public_height"),
        "public_review_status": review_status(record),
        "reviewed_at": record.get("reviewed_at"),
        "issue_type": _issue_type(record.get("issue_type")),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "coordinate_source": record.get("coordinate_source"),
        "position_updated_at": record.get("position_updated_at"),
        "captured_at": record.get("captured_at"),
        "links": record.get("links") or {},
    }
    if is_approved(record):
        summary["public_image"] = _public_file_url(photo_id, "public-image")
        summary["public_thumb"] = _public_file_url(photo_id, "public-thumb")
    return summary


def _owner_review_item(record: dict[str, Any]) -> dict[str, Any]:
    photo_id = str(record["id"])
    return {
        "scope": "field",
        "id": f"field:{photo_id}",
        "photo_id": photo_id,
        "created_at": record.get("created_at"),
        "original_filename": record.get("original_filename"),
        "issue_type": _issue_type(record.get("issue_type")),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "captured_at": record.get("captured_at"),
        "public_review_status": record.get("public_review_status"),
        "reviewed_at": record.get("reviewed_at"),
        "redactions": record.get("redactions") or [],
        "original_image": f"/api/field-photos/{photo_id}/owner-original",
        "public_image": _public_file_url(photo_id, "public-image") if is_approved(record) else None,
        "public_thumb": _public_file_url(photo_id, "public-thumb") if is_approved(record) else None,
    }


def _require_edit_token(record: dict[str, Any], edit_token: Any) -> None:
    if not verify_photo_edit_token(edit_token, record.get("edit_token_salt"), record.get("edit_token_hash")):
        raise PermissionError("Nieprawidłowy token edycji zdjęcia.")


def list_field_photos(storage_dir: Path, *, private_dir: Path | None = None) -> list[dict[str, Any]]:
    private_root = _private_dir(private_dir)
    records: list[dict[str, Any]] = []
    for record in _list_field_records(storage_dir):
        try:
            record_dir = _record_dir_for(str(record["id"]), storage_dir)
            if _prepare_field_record(record_dir, record, private_root):
                _save_field_record(storage_dir, record)
        except (OSError, ValueError, FileNotFoundError):
            continue
        status = review_status(record)
        if isinstance(record, dict) and record.get("id") and status not in {"draft", "rejected"}:
            records.append(_summary(record))
    return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def list_owner_field_photo_review_items(
    photo_ids: list[Any],
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> list[dict[str, Any]]:
    normalize_photo_edit_token(edit_token)
    private_root = _private_dir(private_dir)
    requested_ids: list[str] = []
    for raw_photo_id in photo_ids:
        photo_id = str(raw_photo_id or "").strip()
        if photo_id and photo_id not in requested_ids:
            requested_ids.append(_validate_photo_id(photo_id))
    if not requested_ids:
        raise ValueError("Wskaż zdjęcie do edycji.")

    items: list[dict[str, Any]] = []
    for photo_id in requested_ids:
        record_dir = _record_dir_for(photo_id, storage_dir)
        try:
            record = _load_field_record(record_dir, private_root)
        except FileNotFoundError:
            continue
        try:
            _require_edit_token(record, edit_token)
        except PermissionError:
            continue
        items.append(_owner_review_item(record))
    if not items:
        raise PermissionError("Nieprawidłowy token edycji zdjęcia.")
    return sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def list_field_photo_review_items(storage_dir: Path, *, private_dir: Path | None = None) -> list[dict[str, Any]]:
    private_root = _private_dir(private_dir)
    records: list[dict[str, Any]] = []
    for record in _list_field_records(storage_dir):
        try:
            record_dir = _record_dir_for(str(record["id"]), storage_dir)
            if _prepare_field_record(record_dir, record, private_root):
                _save_field_record(storage_dir, record)
        except (OSError, ValueError, FileNotFoundError):
            continue
        if not isinstance(record, dict) or not record.get("id") or review_status(record) == "draft":
            continue
        photo_id = str(record["id"])
        records.append(
            {
                "scope": "field",
                "id": f"field:{photo_id}",
                "photo_id": photo_id,
                "created_at": record.get("created_at"),
                "original_filename": record.get("original_filename"),
                "issue_type": _issue_type(record.get("issue_type")),
                "lat": record.get("lat"),
                "lon": record.get("lon"),
                "captured_at": record.get("captured_at"),
                "public_review_status": record.get("public_review_status"),
                "reviewed_at": record.get("reviewed_at"),
                "redactions": record.get("redactions") or [],
                "original_image": f"/api/admin/photos/field/{photo_id}/original",
                "public_image": _public_file_url(photo_id, "public-image") if is_approved(record) else None,
                "public_thumb": _public_file_url(photo_id, "public-thumb") if is_approved(record) else None,
            }
        )
    return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def save_field_photo(
    upload: UploadedFile,
    storage_dir: Path,
    *,
    map_lat: Any = None,
    map_lon: Any = None,
    issue_type: Any = None,
    private_dir: Path | None = None,
    submission_owner: str | None = None,
    edit_token: Any = None,
    public_review_status: Any = "pending",
) -> dict[str, Any]:
    private_root = _private_dir(private_dir)
    if upload.field_name != "photo":
        raise ValueError("Nie znaleziono pola pliku 'photo'.")
    size = len(upload.data)
    if size <= 0:
        raise ValueError("Dodaj zdjęcie do uploadu.")
    if size > config.MAX_FIELD_PHOTO_BYTES:
        raise ValueError("Zdjęcie przekracza limit 10 MB.")
    issue_type_text = _issue_type(issue_type)
    review_status_text = str(public_review_status or "pending").strip()
    if review_status_text not in REVIEW_STATUSES:
        raise ValueError("Nieprawidłowy status przeglądu zdjęcia.")

    try:
        with Image.open(io.BytesIO(upload.data)) as image:
            image_format = str(image.format or "").upper()
            if image_format not in config.ALLOWED_UPLOAD_IMAGE_FORMATS:
                raise ValueError("Dozwolone są tylko zdjęcia JPG, PNG albo WebP.")
            exif = image.getexif()
            lat, lon, coordinate_source = _map_coordinates_from(map_lat, map_lon)
            width, height = image.size
    except UnidentifiedImageError as exc:
        raise ValueError("Plik nie jest obsługiwanym zdjęciem.") from exc

    ext, content_type = config.ALLOWED_UPLOAD_IMAGE_FORMATS[image_format]
    photo_id = _photo_id(upload)
    record_dir = storage_dir / photo_id
    record_dir.mkdir(parents=True, exist_ok=False)

    private_original_file = f"field_photos/{photo_id}/original{ext}"
    record = {
        "id": photo_id,
        "created_at": _now_iso(),
        "original_filename": _safe_original_name(upload.filename, ext),
        "content_type": content_type,
        "format": image_format,
        "size_bytes": size,
        "image_width": width,
        "image_height": height,
        "issue_type": issue_type_text,
        "lat": lat,
        "lon": lon,
        "coordinate_source": coordinate_source,
        "captured_at": _captured_at(exif),
        "exif": _limited_exif(exif),
        "private_original_file": private_original_file,
        "public_review_status": review_status_text,
        "redactions": [],
        "reviewed_at": None,
        "submission_owner": submission_owner,
        "links": _links(lat, lon),
    }
    if edit_token is not None and str(edit_token).strip():
        record.update(new_photo_edit_token_hash(edit_token))
        record["edit_token_created_at"] = _now_iso()
    original_path = safe_child(private_root, private_original_file)
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(upload.data)
    _save_field_record(storage_dir, record)
    return {"status": "ok", "photo": _summary(record)}


def update_field_photo_location(
    photo_id: str,
    storage_dir: Path,
    *,
    lat: Any,
    lon: Any,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    record = _load_field_record(record_dir, _private_dir(private_dir))
    lat_float, lon_float = _validated_lat_lon(lat, lon)
    record["lat"] = lat_float
    record["lon"] = lon_float
    record["coordinate_source"] = "manual"
    record["position_updated_at"] = _now_iso()
    record["links"] = _links(lat_float, lon_float)
    _save_field_record(storage_dir, record)
    return {"status": "ok", "photo": _summary(record)}


def delete_field_photo(photo_id: str, storage_dir: Path, *, private_dir: Path | None = None) -> dict[str, Any]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    private_root = _private_dir(private_dir)
    record = _load_field_record(record_dir, private_root)
    try:
        private_rel = record.get("private_original_file")
        original = safe_child(private_root, private_rel) if private_rel else None
        if original and original.exists():
            original.unlink()
        if original:
            remove_empty_private_photo_dir(private_root, photo_id, original)
    except (FileNotFoundError, ValueError):
        pass
    if record_dir.exists():
        shutil.rmtree(record_dir)
    _delete_field_record(storage_dir, photo_id)
    return {"status": "ok", "deleted": photo_id}


def field_photo_asset(
    photo_id: str,
    storage_dir: Path,
    asset: Literal["public-image", "public-thumb", "original"],
    *,
    private_dir: Path | None = None,
) -> tuple[Path, str]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    private_root = _private_dir(private_dir)
    record = _load_field_record(record_dir, private_root)
    if asset == "public-thumb":
        if not is_approved(record):
            raise FileNotFoundError("Nie znaleziono publicznej miniatury zdjęcia.")
        file_name = str(record.get("public_thumb_file") or "")
        content_type = "image/jpeg"
        path = safe_child(record_dir, file_name)
    elif asset == "public-image":
        if not is_approved(record):
            raise FileNotFoundError("Nie znaleziono publicznej kopii zdjęcia.")
        file_name = str(record.get("public_image_file") or "")
        content_type = "image/jpeg"
        path = safe_child(record_dir, file_name)
    else:
        file_name = str(record.get("private_original_file") or "")
        content_type = str(record.get("content_type") or "application/octet-stream")
        path = safe_child(private_root, file_name)
    if not path.exists():
        raise FileNotFoundError("Nie znaleziono pliku zdjęcia terenowego.")
    return path, content_type


def field_photo_owner_original_asset(
    photo_id: str,
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> tuple[Path, str]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    private_root = _private_dir(private_dir)
    record = _load_field_record(record_dir, private_root)
    _require_edit_token(record, edit_token)
    return field_photo_asset(photo_id, storage_dir, "original", private_dir=private_root)


def review_field_photo(
    photo_id: str,
    storage_dir: Path,
    *,
    status: Any,
    redactions: Any,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    record = _load_field_record(record_dir, _private_dir(private_dir))
    apply_review_update(
        record,
        record_dir,
        _private_dir(private_dir),
        status=status,
        redactions=redactions,
        thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
        thumb_quality=config.FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY,
    )
    _save_field_record(storage_dir, record)
    return {"status": "ok", "photo": _summary(record) if is_approved(record) else {"id": record["id"]}}


def review_field_photo_by_owner(
    photo_id: str,
    edit_token: Any,
    storage_dir: Path,
    *,
    redactions: Any,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    record_dir = _record_dir_for(photo_id, storage_dir)
    record = _load_field_record(record_dir, _private_dir(private_dir))
    _require_edit_token(record, edit_token)
    status = "draft" if review_status(record) == "draft" else "pending"
    apply_review_update(
        record,
        record_dir,
        _private_dir(private_dir),
        status=status,
        redactions=redactions,
        thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
        thumb_quality=config.FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY,
    )
    record["owner_redactions_updated_at"] = _now_iso()
    _save_field_record(storage_dir, record)
    return {"status": "ok", "photo": _summary(record)}


def submit_field_photos_by_owner(
    photo_ids: list[Any],
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    normalize_photo_edit_token(edit_token)
    private_root = _private_dir(private_dir)
    requested_ids: list[str] = []
    for raw_photo_id in photo_ids:
        photo_id = str(raw_photo_id or "").strip()
        if photo_id and photo_id not in requested_ids:
            requested_ids.append(_validate_photo_id(photo_id))
    if not requested_ids:
        raise ValueError("Wskaż zdjęcie do wysłania.")

    photos: list[dict[str, Any]] = []
    for photo_id in requested_ids:
        record_dir = _record_dir_for(photo_id, storage_dir)
        try:
            record = _load_field_record(record_dir, private_root)
        except FileNotFoundError:
            continue
        try:
            _require_edit_token(record, edit_token)
        except PermissionError:
            continue
        status = review_status(record)
        if status == "draft":
            record["public_review_status"] = "pending"
            record["submitted_at"] = _now_iso()
            record["reviewed_at"] = None
            remove_public_derivatives(record, record_dir)
            _save_field_record(storage_dir, record)
            status = "pending"
        if status == "pending":
            photos.append(_summary(record))
    if not photos:
        raise PermissionError("Nieprawidłowy token edycji zdjęcia albo zdjęcie nie jest szkicem.")
    return {"status": "ok", "photos": sorted(photos, key=lambda item: str(item.get("created_at") or ""), reverse=True)}


def discard_field_photo_drafts_by_owner(
    photo_ids: list[Any],
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    normalize_photo_edit_token(edit_token)
    private_root = _private_dir(private_dir)
    draft_ids: list[str] = []
    for raw_photo_id in photo_ids:
        photo_id = str(raw_photo_id or "").strip()
        if not photo_id or photo_id in draft_ids:
            continue
        photo_id = _validate_photo_id(photo_id)
        record_dir = _record_dir_for(photo_id, storage_dir)
        try:
            record = _load_field_record(record_dir, private_root)
        except FileNotFoundError:
            continue
        try:
            _require_edit_token(record, edit_token)
        except PermissionError:
            continue
        if review_status(record) == "draft":
            draft_ids.append(photo_id)
    if not draft_ids:
        raise PermissionError("Nieprawidłowy token edycji zdjęcia albo szkic został już wysłany.")

    deleted: list[str] = []
    for photo_id in draft_ids:
        result = delete_field_photo(photo_id, storage_dir, private_dir=private_root)
        deleted_id = str(result.get("deleted") or "")
        if deleted_id:
            deleted.append(deleted_id)
    return {"status": "ok", "deleted": deleted}

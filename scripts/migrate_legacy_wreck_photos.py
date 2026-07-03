#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core import config
from core.field_photos import FIELD_PHOTO_ID_RE
from core.geo import external_map_links
from core.json_io import write_json_atomic
from core.photo_privacy import (
    ensure_review_fields,
    generate_public_derivatives,
    is_approved,
    private_original_rel,
    safe_child,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, payload)


def _valid_photo_id(value: Any) -> str | None:
    photo_id = str(value or "").strip()
    return photo_id if FIELD_PHOTO_ID_RE.fullmatch(photo_id) else None


def _safe_existing_child(base_dir: Path, relative_path: Any) -> Path | None:
    try:
        path = safe_child(base_dir, relative_path)
    except ValueError:
        return None
    return path if path.exists() else None


def _image_metadata(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        with Image.open(path) as image:
            return {
                "format": str(image.format or "").upper() or None,
                "image_width": image.width,
                "image_height": image.height,
            }
    except (OSError, UnidentifiedImageError):
        return {}


def _content_type(image_format: Any) -> str:
    normalized = str(image_format or "").upper()
    return {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
    }.get(normalized, "image/jpeg")


def _private_source_path(record_dir: Path, private_dir: Path, photo: dict[str, Any]) -> Path | None:
    private_path = _safe_existing_child(private_dir, photo.get("private_original_file"))
    if private_path:
        return private_path
    return _safe_existing_child(record_dir, photo.get("original_file"))


def _public_source_path(record_dir: Path, photo: dict[str, Any], key: str) -> Path | None:
    path = _safe_existing_child(record_dir, photo.get(key))
    if path:
        return path
    if key == "public_thumb_file":
        return _safe_existing_child(record_dir, photo.get("thumb_file"))
    return None


def _copy_file(source: Path | None, destination: Path, *, dry_run: bool) -> bool:
    if not source or not source.exists() or destination.exists():
        return False
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return True


def _lat_lon(wreck: dict[str, Any], photo: dict[str, Any]) -> tuple[float, float]:
    lat = photo.get("field_photo_lat", wreck.get("lat"))
    lon = photo.get("field_photo_lon", wreck.get("lon"))
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError) as exc:
        raise ValueError("Brak poprawnych współrzędnych zdjęcia terenowego.") from exc


def _record_from_attached(
    *,
    wreck: dict[str, Any],
    photo: dict[str, Any],
    private_source: Path,
    private_rel: str,
) -> dict[str, Any]:
    photo_id = str(photo["id"])
    lat, lon = _lat_lon(wreck, photo)
    metadata = _image_metadata(private_source)
    image_format = photo.get("format") or metadata.get("format") or "JPEG"
    created_at = (
        photo.get("field_photo_created_at")
        or photo.get("created_at")
        or wreck.get("created_at")
        or _now_iso()
    )
    record = {
        "id": photo_id,
        "created_at": created_at,
        "original_filename": str(photo.get("original_filename") or f"{photo_id}.jpg"),
        "content_type": photo.get("content_type") or _content_type(image_format),
        "format": image_format,
        "size_bytes": photo.get("size_bytes") or private_source.stat().st_size,
        "image_width": photo.get("image_width") or metadata.get("image_width"),
        "image_height": photo.get("image_height") or metadata.get("image_height"),
        "issue_type": config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE,
        "lat": lat,
        "lon": lon,
        "coordinate_source": "map",
        "captured_at": photo.get("captured_at"),
        "exif": photo.get("exif") if isinstance(photo.get("exif"), dict) else {},
        "private_original_file": private_rel,
        "public_review_status": photo.get("public_review_status") or "approved",
        "redactions": photo.get("redactions") if isinstance(photo.get("redactions"), list) else [],
        "reviewed_at": photo.get("reviewed_at"),
        "submission_owner": wreck.get("submission_owner"),
        "links": external_map_links(lat, lon),
    }
    ensure_review_fields(record)
    return record


def _normalize_existing_record(
    record: dict[str, Any],
    *,
    wreck: dict[str, Any],
    photo: dict[str, Any],
) -> bool:
    changed = ensure_review_fields(record)
    if record.pop("attached_wreck_id", None) is not None:
        changed = True
    if record.pop("attached_at", None) is not None:
        changed = True
    if record.get("issue_type") != config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE:
        record["issue_type"] = config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE
        changed = True
    if not record.get("links"):
        lat, lon = _lat_lon(wreck, photo)
        record["links"] = external_map_links(lat, lon)
        changed = True
    return changed


def migrate(
    *,
    wrecks_dir: Path,
    field_photos_dir: Path,
    private_dir: Path,
    dry_run: bool,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "status": "ok",
        "dry_run": dry_run,
        "created": [],
        "normalized": [],
        "skipped": [],
        "copied_private_originals": 0,
        "copied_public_files": 0,
    }
    seen: set[str] = set()
    for record_path in sorted(wrecks_dir.glob("*/record.json")):
        wreck_dir = record_path.parent
        try:
            wreck = _read_json(record_path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(wreck, dict):
            continue
        photos = wreck.get("attached_photos") if isinstance(wreck.get("attached_photos"), list) else []
        for photo in photos:
            if not isinstance(photo, dict):
                continue
            photo_id = _valid_photo_id(photo.get("id"))
            if not photo_id or photo_id in seen:
                continue
            seen.add(photo_id)
            private_source = _private_source_path(wreck_dir, private_dir, photo)
            if not private_source:
                manifest["skipped"].append(
                    {"photo_id": photo_id, "wreck_id": wreck.get("id"), "reason": "missing_private_original"}
                )
                continue
            field_dir = field_photos_dir / photo_id
            record_out = field_dir / "record.json"
            private_rel = private_original_rel("field_photos", photo_id, private_source.suffix or ".jpg")
            private_destination = safe_child(private_dir, private_rel)

            if record_out.exists():
                field_record = _read_json(record_out)
                if not isinstance(field_record, dict):
                    manifest["skipped"].append(
                        {"photo_id": photo_id, "wreck_id": wreck.get("id"), "reason": "bad_field_record"}
                    )
                    continue
                if _normalize_existing_record(field_record, wreck=wreck, photo=photo):
                    if not dry_run:
                        _write_json(record_out, field_record)
                    manifest["normalized"].append(photo_id)
                continue

            field_record = _record_from_attached(
                wreck=wreck,
                photo=photo,
                private_source=private_source,
                private_rel=private_rel,
            )
            if _copy_file(private_source, private_destination, dry_run=dry_run):
                manifest["copied_private_originals"] += 1
            public_image_source = _public_source_path(wreck_dir, photo, "public_image_file")
            public_thumb_source = _public_source_path(wreck_dir, photo, "public_thumb_file")
            if _copy_file(public_image_source, field_dir / "public.jpg", dry_run=dry_run):
                field_record["public_image_file"] = "public.jpg"
                manifest["copied_public_files"] += 1
            if _copy_file(public_thumb_source, field_dir / "public_thumb.jpg", dry_run=dry_run):
                field_record["public_thumb_file"] = "public_thumb.jpg"
                manifest["copied_public_files"] += 1
            if not dry_run:
                field_dir.mkdir(parents=True, exist_ok=True)
                if is_approved(field_record):
                    generate_public_derivatives(
                        field_record,
                        field_dir,
                        private_dir,
                        thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
                        thumb_quality=config.FIELD_PHOTO_THUMBNAIL_JPEG_QUALITY,
                    )
                _write_json(record_out, field_record)
            manifest["created"].append(photo_id)
    manifest["created_count"] = len(manifest["created"])
    manifest["normalized_count"] = len(manifest["normalized"])
    manifest["skipped_count"] = len(manifest["skipped"])
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Przenies stare zdjecia spraw pojazdow do wzorca zdjec terenowych.")
    parser.add_argument("--wrecks-dir", type=Path, default=config.WRECKS_DIR)
    parser.add_argument("--field-photos-dir", type=Path, default=config.FIELD_PHOTOS_DIR)
    parser.add_argument("--private-dir", type=Path, default=config.PRIVATE_PHOTOS_DIR)
    parser.add_argument("--apply", action="store_true", help="Zapisz zmiany. Bez tej flagi skrypt robi tylko audyt.")
    parser.add_argument("--manifest", type=Path, default=config.DIAGNOSTICS_DIR / "legacy_wreck_photo_migration.json")
    args = parser.parse_args()

    result = migrate(
        wrecks_dir=args.wrecks_dir,
        field_photos_dir=args.field_photos_dir,
        private_dir=args.private_dir,
        dry_run=not args.apply,
    )
    if args.apply:
        _write_json(args.manifest, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" and not result["skipped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.wrecks_rendering import approved_attached_photos


def wreck_public_file_url(record_id: str, relative_path: Any) -> str | None:
    rel = str(relative_path or "").replace("\\", "/").strip("/")
    if not rel or rel.startswith("/") or any(part in {"", ".", ".."} for part in rel.split("/")):
        return None
    return f"/zidentyfikowane_wraki/{quote(record_id, safe='')}/{quote(rel, safe='/._-')}"


def evidence_previews(record: dict[str, Any]) -> list[dict[str, str]]:
    record_id = str(record.get("id") or "")
    previews: list[dict[str, str]] = []

    latest = record.get("latest_evidence") if isinstance(record.get("latest_evidence"), dict) else {}
    evidence_path = str(latest.get("path") or "").strip("/")
    crops = latest.get("crops") if isinstance(latest.get("crops"), list) else []
    for crop in crops:
        if not isinstance(crop, dict):
            continue
        file_name = str(crop.get("file") or "").strip("/")
        if not file_name:
            continue
        url = wreck_public_file_url(record_id, f"{evidence_path}/{file_name}")
        if not url:
            continue
        label = str(crop.get("label") or "evidence")
        previews.append(
            {
                "source": "evidence",
                "label": label,
                "public_image": url,
                "public_thumb": url,
            }
        )
    return previews


def field_photo_previews(record: dict[str, Any]) -> list[dict[str, str]]:
    record_id = str(record.get("id") or "")
    previews: list[dict[str, str]] = []

    for photo in approved_attached_photos(record):
        thumb_url = wreck_public_file_url(record_id, photo.get("public_thumb_file"))
        public_url = wreck_public_file_url(record_id, photo.get("public_image_file")) or thumb_url
        if not thumb_url:
            continue
        label = str(photo.get("original_filename") or "photo")
        previews.append(
            {
                "source": "attached",
                "label": label,
                "public_image": public_url or thumb_url,
                "public_thumb": thumb_url,
            }
        )
    return previews


def wreck_summary(record: dict[str, Any]) -> dict[str, Any]:
    latest = record.get("latest_evidence") or {}
    all_attached_photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    attached_photos = approved_attached_photos(record)
    return {
        "id": record["id"],
        "status": record.get("status", "confirmed"),
        "public_review_status": record.get("public_review_status"),
        "reviewed_at": record.get("reviewed_at"),
        "lat": record.get("lat"),
        "lon": record.get("lon"),
        "best_score": record.get("best_score"),
        "labels_present": record.get("labels_present") or [],
        "first_seen_year": record.get("first_seen_year"),
        "last_seen_year": record.get("last_seen_year"),
        "evidence_count": len(record.get("evidences") or []),
        "updated_at": record.get("updated_at"),
        "latest_evidence_id": latest.get("id"),
        "photo_count": len(attached_photos),
        "review_photo_count": len(all_attached_photos),
        "evidence_previews": evidence_previews(record),
        "field_photo_previews": field_photo_previews(record),
        "folder_url": f"/zidentyfikowane_wraki/{record['id']}/index.html",
        "links": record.get("links") or {},
    }

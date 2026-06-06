from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.photo_privacy import REVIEW_STATUSES, is_approved, normalize_redactions
from core.photo_privacy import now_iso as privacy_now_iso
from core.wrecks_public import wreck_public_file_url


def validate_review_status(status: Any, *, subject: str) -> str:
    status_text = str(status or "").strip()
    if status_text not in REVIEW_STATUSES:
        if subject == "photo":
            raise ValueError("Nieprawidłowy status przeglądu zdjęcia.")
        raise ValueError("Nieprawidłowy status przeglądu sprawy.")
    return status_text


def reviewed_at_for(status_text: str) -> str | None:
    return privacy_now_iso() if status_text in {"approved", "rejected"} else None


def wreck_review_items(records: list[dict[str, Any]], *, status: str = "pending") -> list[dict[str, Any]]:
    items = []
    for record in records:
        review_status = str(record.get("public_review_status") or "pending")
        if status != "all" and review_status != status:
            continue
        items.append(
            {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "public_review_status": review_status,
                "reviewed_at": record.get("reviewed_at"),
                "lat": record.get("lat"),
                "lon": record.get("lon"),
                "source": record.get("source") or record.get("status"),
                "photo_count": len(record.get("attached_photos") or []),
                "evidence_count": len(record.get("evidences") or []),
                "links": record.get("links") or {},
                "folder_url": f"/zidentyfikowane_wraki/{record['id']}/index.html",
            }
        )
    return sorted(items, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)


def apply_wreck_review(record: dict[str, Any], *, status: Any, updated_at: str) -> str:
    status_text = validate_review_status(status, subject="wreck")
    record["public_review_status"] = status_text
    record["reviewed_at"] = reviewed_at_for(status_text)
    record["updated_at"] = updated_at
    return status_text


def wreck_photo_review_items(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in records:
        wreck_id = str(record.get("id") or "")
        for photo in record.get("attached_photos") or []:
            if isinstance(photo, dict):
                item = wreck_photo_review_item(wreck_id, photo)
                if item:
                    items.append(item)
    return sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def wreck_photo_review_item(wreck_id: str, photo: dict[str, Any]) -> dict[str, Any] | None:
    photo_id = str(photo.get("id") or "")
    if not photo_id:
        return None
    public_image = wreck_public_file_url(wreck_id, photo.get("public_image_file")) if is_approved(photo) else None
    public_thumb = wreck_public_file_url(wreck_id, photo.get("public_thumb_file")) if is_approved(photo) else None
    return {
        "scope": "wreck",
        "id": f"wreck:{wreck_id}:{photo_id}",
        "wreck_id": wreck_id,
        "photo_id": photo_id,
        "created_at": photo.get("created_at"),
        "original_filename": photo.get("original_filename"),
        "public_review_status": photo.get("public_review_status"),
        "reviewed_at": photo.get("reviewed_at"),
        "redactions": photo.get("redactions") or [],
        "original_image": f"/api/admin/photos/wreck/{quote(wreck_id, safe='')}/{quote(photo_id, safe='')}/original",
        "public_image": public_image,
        "public_thumb": public_thumb,
    }


def apply_wreck_photo_review(photo: dict[str, Any], *, status: Any, redactions: Any) -> str:
    status_text = validate_review_status(status, subject="photo")
    photo["redactions"] = normalize_redactions(redactions)
    photo["public_review_status"] = status_text
    photo["reviewed_at"] = reviewed_at_for(status_text)
    return status_text

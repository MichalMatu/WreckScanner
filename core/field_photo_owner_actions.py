from __future__ import annotations

from pathlib import Path
from typing import Any

from core.field_photos import (
    _FIELD_PHOTO_MUTATION_LOCK,
    _delete_loaded_field_photo,
    _load_field_record,
    _private_dir,
    _record_dir_for,
    _require_edit_token,
    _validate_photo_id,
)
from core.photo_privacy import review_status
from core.photo_tokens import normalize_photo_edit_token


def _dedup_photo_ids(photo_ids: list[Any], empty_message: str) -> list[str]:
    requested_ids: list[str] = []
    for raw_photo_id in photo_ids:
        photo_id = str(raw_photo_id or "").strip()
        if photo_id and photo_id not in requested_ids:
            requested_ids.append(_validate_photo_id(photo_id))
    if not requested_ids:
        raise ValueError(empty_message)
    return requested_ids


def delete_field_photos_by_owner(
    photo_ids: list[Any],
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
    allowed_review_statuses: set[str] | frozenset[str] = frozenset({"draft", "pending"}),
) -> dict[str, Any]:
    normalize_photo_edit_token(edit_token)
    requested_ids = _dedup_photo_ids(photo_ids, "Wskaż zdjęcie do usunięcia.")
    private_root = _private_dir(private_dir)
    deleted: list[str] = []
    with _FIELD_PHOTO_MUTATION_LOCK:
        deletion_plan: list[tuple[str, Path, dict[str, Any]]] = []
        for photo_id in requested_ids:
            record_dir = _record_dir_for(photo_id, storage_dir)
            record = _load_field_record(record_dir, private_root)
            _require_edit_token(record, edit_token)
            if review_status(record) not in allowed_review_statuses:
                raise PermissionError("Możesz usunąć tylko szkic albo zdjęcie oczekujące na weryfikację.")
            deletion_plan.append((photo_id, record_dir, record))

        for photo_id, record_dir, record in deletion_plan:
            result = _delete_loaded_field_photo(
                photo_id,
                storage_dir,
                record_dir=record_dir,
                private_root=private_root,
                record=record,
            )
            deleted_id = str(result.get("deleted") or "")
            if deleted_id:
                deleted.append(deleted_id)
    return {"status": "ok", "deleted": deleted}


def discard_field_photo_drafts_by_owner(
    photo_ids: list[Any],
    edit_token: Any,
    storage_dir: Path,
    *,
    private_dir: Path | None = None,
) -> dict[str, Any]:
    normalize_photo_edit_token(edit_token)
    private_root = _private_dir(private_dir)
    deleted: list[str] = []
    with _FIELD_PHOTO_MUTATION_LOCK:
        deletion_plan: list[tuple[str, Path, dict[str, Any]]] = []
        for photo_id in _dedup_photo_ids(photo_ids, "Wskaż zdjęcie do porzucenia."):
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
                deletion_plan.append((photo_id, record_dir, record))
        if not deletion_plan:
            raise PermissionError("Nieprawidłowy token edycji zdjęcia albo szkic został już wysłany.")

        for photo_id, record_dir, record in deletion_plan:
            result = _delete_loaded_field_photo(
                photo_id,
                storage_dir,
                record_dir=record_dir,
                private_root=private_root,
                record=record,
            )
            deleted_id = str(result.get("deleted") or "")
            if deleted_id:
                deleted.append(deleted_id)
    return {"status": "ok", "deleted": deleted}

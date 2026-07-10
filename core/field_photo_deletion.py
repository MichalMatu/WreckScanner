from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Any

from core.field_photo_store import delete_field_records
from core.photo_privacy import remove_empty_private_photo_dir, safe_child

DeletionPlan = list[tuple[str, Path, dict[str, Any]]]


def _restore_staged_paths(staged_paths: list[tuple[Path, Path]]) -> None:
    for active_path, staged_path in reversed(staged_paths):
        if not staged_path.exists() and not staged_path.is_symlink():
            continue
        if active_path.exists() or active_path.is_symlink():
            raise RuntimeError(f"Nie można wycofać usuwania; ścieżka docelowa już istnieje: {active_path}")
        staged_path.replace(active_path)


def _stage_paths(active_paths: list[Path]) -> list[tuple[Path, Path]]:
    token = secrets.token_hex(12)
    staged_paths: list[tuple[Path, Path]] = []
    seen: set[Path] = set()
    try:
        for active_path in active_paths:
            if active_path in seen:
                raise ValueError(f"Powtórzona ścieżka w planie usuwania: {active_path}")
            seen.add(active_path)
            if not active_path.exists() and not active_path.is_symlink():
                continue
            staged_path = active_path.with_name(f".{active_path.name}.deleting-{token}")
            if staged_path.exists() or staged_path.is_symlink():
                raise FileExistsError(f"Ścieżka stagingowa usuwania już istnieje: {staged_path}")
            active_path.replace(staged_path)
            staged_paths.append((active_path, staged_path))
    except Exception:
        _restore_staged_paths(staged_paths)
        raise
    return staged_paths


def _remove_staged_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def delete_loaded_field_photos(
    deletion_plan: DeletionPlan,
    storage_dir: Path,
    *,
    private_root: Path,
) -> list[str]:
    if not deletion_plan:
        raise ValueError("Brak zdjęć w planie usuwania.")

    active_paths: list[Path] = []
    private_originals: list[tuple[str, Path]] = []
    photo_ids: list[str] = []
    for photo_id, record_dir, record in deletion_plan:
        photo_ids.append(photo_id)
        active_paths.append(record_dir)
        private_rel = record.get("private_original_file")
        if private_rel:
            original = safe_child(private_root, private_rel)
            active_paths.append(original)
            private_originals.append((photo_id, original))

    staged_paths = _stage_paths(active_paths)
    try:
        delete_field_records(storage_dir, photo_ids)
    except Exception:
        _restore_staged_paths(staged_paths)
        raise

    for _, staged_path in staged_paths:
        _remove_staged_path(staged_path)
    for photo_id, original in private_originals:
        remove_empty_private_photo_dir(private_root, photo_id, original)
    return photo_ids

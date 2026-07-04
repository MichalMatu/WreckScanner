from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core import config
from core.database import apply_migrations, connect_database, upsert_field_photo

FIELD_PHOTO_ID_RE = re.compile(r"photo_\d{8}T\d{6}Z_[a-f0-9]{8}")


def validate_photo_id(photo_id: str) -> str:
    if not FIELD_PHOTO_ID_RE.fullmatch(photo_id):
        raise ValueError("Nieprawidłowy identyfikator zdjęcia.")
    return photo_id


def database_path_for(storage_dir: Path) -> Path:
    if storage_dir == config.FIELD_PHOTOS_DIR:
        return config.DATABASE_PATH
    if storage_dir.name == config.FIELD_PHOTOS_DIR.name:
        return storage_dir.parent / config.DATABASE_PATH.name
    return storage_dir / config.DATABASE_PATH.name


def connection_for(storage_dir: Path):
    connection = connect_database(database_path_for(storage_dir))
    apply_migrations(connection)
    return connection


def record_from_row(row: Any) -> dict[str, Any]:
    record = dict(row)
    record["redactions"] = json.loads(str(record.pop("redactions_json") or "[]"))
    record["exif"] = json.loads(str(record.pop("exif_json") or "{}"))
    record["links"] = json.loads(str(record.pop("links_json") or "{}"))
    return record


def save_field_record(storage_dir: Path, record: dict[str, Any]) -> None:
    connection = connection_for(storage_dir)
    try:
        with connection:
            upsert_field_photo(connection, record)
    finally:
        connection.close()


def delete_field_record(storage_dir: Path, photo_id: str) -> None:
    connection = connection_for(storage_dir)
    try:
        with connection:
            connection.execute("DELETE FROM field_photos WHERE id = ?", (photo_id,))
    finally:
        connection.close()


def load_field_record_by_id(photo_id: str, storage_dir: Path) -> dict[str, Any]:
    photo_id = validate_photo_id(photo_id)
    connection = connection_for(storage_dir)
    try:
        row = connection.execute("SELECT * FROM field_photos WHERE id = ?", (photo_id,)).fetchone()
    finally:
        connection.close()
    if row is None:
        raise FileNotFoundError("Nie znaleziono zdjęcia terenowego.")
    return record_from_row(row)


def list_field_records(storage_dir: Path) -> list[dict[str, Any]]:
    connection = connection_for(storage_dir)
    try:
        rows = connection.execute("SELECT * FROM field_photos ORDER BY created_at DESC, id DESC").fetchall()
    finally:
        connection.close()
    return [record_from_row(row) for row in rows]

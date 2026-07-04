from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config
from core.photo_privacy import safe_existing_child

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class JsonToDatabaseReport:
    database_path: Path
    field_photo_records: int
    migrated_field_photos: int
    settings_records: int
    migrated_settings: int
    privacy_request_records: int
    migrated_privacy_requests: int


@dataclass(frozen=True)
class DatabaseValidationReport:
    field_photo_records: int
    database_field_photos: int
    settings_records: int
    database_settings: int
    privacy_request_records: int
    database_privacy_requests: int
    missing_paths: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_text(value: Any, fallback: Any) -> str:
    payload = value if value is not None else fallback
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Nieprawidlowy JSON obiektu: {path}")
    return payload


def connect_database(database_path: Path = config.DATABASE_PATH) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migration_paths(migrations_dir: Path = config.DATABASE_MIGRATIONS_DIR, *, root_dir: Path = ROOT_DIR) -> list[Path]:
    root = root_dir.resolve()
    migrations_path = migrations_dir if migrations_dir.is_absolute() else root / migrations_dir
    return sorted(migrations_path.glob("*.sql"))


def applied_migrations(connection: sqlite3.Connection) -> set[str]:
    try:
        rows = connection.execute("SELECT version FROM schema_migrations")
    except sqlite3.OperationalError:
        return set()
    return {str(row["version"]) for row in rows}


def apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: Path = config.DATABASE_MIGRATIONS_DIR,
    *,
    root_dir: Path = ROOT_DIR,
) -> list[str]:
    applied = applied_migrations(connection)
    applied_now: list[str] = []
    for path in migration_paths(migrations_dir, root_dir=root_dir):
        version = path.stem
        if version in applied:
            continue
        connection.executescript(path.read_text(encoding="utf-8"))
        connection.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version,))
        applied.add(version)
        applied_now.append(version)
    return applied_now


def has_restic_snapshot(root_dir: Path) -> bool:
    snapshots_dir = root_dir / ".backups" / "wreckscanner-restic" / "snapshots"
    return snapshots_dir.is_dir() and any(path.is_file() for path in snapshots_dir.rglob("*"))


def ensure_backup_snapshot(root_dir: Path) -> None:
    if not has_restic_snapshot(root_dir):
        raise ValueError("Przed migracja DB wykonaj backup restic danych aplikacji.")


def field_photo_record_paths(root_dir: Path) -> list[Path]:
    return sorted((root_dir / config.FIELD_PHOTOS_DIR).glob("*/record.json"))


def privacy_request_paths(root_dir: Path) -> list[Path]:
    storage = root_dir / config.PRIVACY_REQUESTS_DIR
    if not storage.is_dir():
        return []
    return sorted(storage.glob("privacy_*.json"))


def require_existing_photo_files(root_dir: Path, record_dir: Path, record: dict[str, Any]) -> None:
    private_rel = record.get("private_original_file")
    if private_rel and not safe_existing_child(root_dir / config.PRIVATE_PHOTOS_DIR, private_rel):
        raise ValueError(f"Brak prywatnego oryginalu dla {record.get('id')}: {private_rel}")
    for key in ("public_image_file", "public_thumb_file"):
        rel = record.get(key)
        if rel and not safe_existing_child(record_dir, rel):
            raise ValueError(f"Brak pliku {key} dla {record.get('id')}: {rel}")


def _field_photo_row(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(record["id"]),
        str(record["created_at"]),
        record.get("submitted_at"),
        record.get("captured_at"),
        str(record["issue_type"]),
        float(record["lat"]),
        float(record["lon"]),
        str(record.get("coordinate_source") or "map"),
        record.get("position_updated_at"),
        str(record["public_review_status"]),
        record.get("reviewed_at"),
        record.get("owner_redactions_updated_at"),
        json_text(record.get("redactions"), []),
        json_text(record.get("exif"), {}),
        str(record["original_filename"]),
        str(record["content_type"]),
        str(record["format"]),
        int(record["size_bytes"]),
        int(record["image_width"]) if record.get("image_width") is not None else None,
        int(record["image_height"]) if record.get("image_height") is not None else None,
        record.get("private_original_file"),
        record.get("private_original_replaced_at"),
        record.get("private_original_deleted_at"),
        record.get("private_original_retention_action"),
        record.get("public_image_file"),
        record.get("public_thumb_file"),
        int(record["public_width"]) if record.get("public_width") is not None else None,
        int(record["public_height"]) if record.get("public_height") is not None else None,
        record.get("submission_owner"),
        record.get("edit_token_salt"),
        record.get("edit_token_hash"),
        record.get("edit_token_created_at"),
        json_text(record.get("links"), {}),
        now_iso(),
    )


def upsert_field_photo(connection: sqlite3.Connection, record: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO field_photos (
            id, created_at, submitted_at, captured_at, issue_type, lat, lon,
            coordinate_source, position_updated_at, public_review_status,
            reviewed_at, owner_redactions_updated_at, redactions_json, exif_json,
            original_filename, content_type, format, size_bytes, image_width,
            image_height, private_original_file, private_original_replaced_at,
            private_original_deleted_at, private_original_retention_action,
            public_image_file, public_thumb_file, public_width, public_height,
            submission_owner, edit_token_salt, edit_token_hash, edit_token_created_at,
            links_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            created_at = excluded.created_at,
            submitted_at = excluded.submitted_at,
            captured_at = excluded.captured_at,
            issue_type = excluded.issue_type,
            lat = excluded.lat,
            lon = excluded.lon,
            coordinate_source = excluded.coordinate_source,
            position_updated_at = excluded.position_updated_at,
            public_review_status = excluded.public_review_status,
            reviewed_at = excluded.reviewed_at,
            owner_redactions_updated_at = excluded.owner_redactions_updated_at,
            redactions_json = excluded.redactions_json,
            exif_json = excluded.exif_json,
            original_filename = excluded.original_filename,
            content_type = excluded.content_type,
            format = excluded.format,
            size_bytes = excluded.size_bytes,
            image_width = excluded.image_width,
            image_height = excluded.image_height,
            private_original_file = excluded.private_original_file,
            private_original_replaced_at = excluded.private_original_replaced_at,
            private_original_deleted_at = excluded.private_original_deleted_at,
            private_original_retention_action = excluded.private_original_retention_action,
            public_image_file = excluded.public_image_file,
            public_thumb_file = excluded.public_thumb_file,
            public_width = excluded.public_width,
            public_height = excluded.public_height,
            submission_owner = excluded.submission_owner,
            edit_token_salt = excluded.edit_token_salt,
            edit_token_hash = excluded.edit_token_hash,
            edit_token_created_at = excluded.edit_token_created_at,
            links_json = excluded.links_json,
            updated_at = excluded.updated_at
        """,
        _field_photo_row(record),
    )


def upsert_settings(connection: sqlite3.Connection, settings_path: Path) -> int:
    if not settings_path.exists():
        return 0
    settings = read_json_object(settings_path)
    updated_at = now_iso()
    for key, value in sorted(settings.items()):
        connection.execute(
            """
            INSERT INTO settings (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (str(key), json_text(value, {}), updated_at),
        )
    return len(settings)


def upsert_privacy_request(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO privacy_requests (
            id, created_at, updated_at, status, email, target, reason, handled_at, admin_note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            created_at = excluded.created_at,
            updated_at = excluded.updated_at,
            status = excluded.status,
            email = excluded.email,
            target = excluded.target,
            reason = excluded.reason,
            handled_at = excluded.handled_at,
            admin_note = excluded.admin_note
        """,
        (
            str(payload["id"]),
            str(payload["created_at"]),
            str(payload.get("updated_at") or payload["created_at"]),
            str(payload.get("status") or "new"),
            str(payload["email"]),
            str(payload["target"]),
            str(payload["reason"]),
            payload.get("handled_at"),
            str(payload.get("admin_note") or ""),
        ),
    )


def validate_database_counts(
    connection: sqlite3.Connection,
    *,
    field_photo_records: int,
    settings_records: int,
    privacy_request_records: int,
) -> None:
    counts = {
        "field_photos": field_photo_records,
        "settings": settings_records,
        "privacy_requests": privacy_request_records,
    }
    for table, expected in counts.items():
        actual = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        if actual != expected:
            raise ValueError(f"Tabela {table} ma {actual} rekordow, oczekiwano {expected}.")


def source_settings_count(root_dir: Path) -> int:
    settings_path = root_dir / config.SETTINGS_FILENAME
    if not settings_path.exists():
        return 0
    return len(read_json_object(settings_path))


def database_missing_paths(root_dir: Path, connection: sqlite3.Connection) -> list[str]:
    missing: list[str] = []
    rows = connection.execute(
        "SELECT id, private_original_file, public_image_file, public_thumb_file FROM field_photos ORDER BY id"
    )
    for row in rows:
        photo_id = str(row["id"])
        private_rel = row["private_original_file"]
        if private_rel and not safe_existing_child(root_dir / config.PRIVATE_PHOTOS_DIR, private_rel):
            missing.append(f"{photo_id}: {private_rel}")
        record_dir = root_dir / config.FIELD_PHOTOS_DIR / photo_id
        for key in ("public_image_file", "public_thumb_file"):
            rel = row[key]
            if rel and not safe_existing_child(record_dir, rel):
                missing.append(f"{photo_id}: {rel}")
    return missing


def validate_database_against_json(
    *,
    root_dir: Path = ROOT_DIR,
    database_path: Path = config.DATABASE_PATH,
) -> DatabaseValidationReport:
    root = root_dir.resolve()
    database = database_path if database_path.is_absolute() else root / database_path
    connection = connect_database(database)
    try:
        field_photo_records = len(field_photo_record_paths(root))
        settings_records = source_settings_count(root)
        privacy_request_records = len(privacy_request_paths(root))
        database_field_photos = int(connection.execute("SELECT COUNT(*) FROM field_photos").fetchone()[0])
        database_settings = int(connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0])
        database_privacy_requests = int(connection.execute("SELECT COUNT(*) FROM privacy_requests").fetchone()[0])
        missing_paths = database_missing_paths(root, connection)
    finally:
        connection.close()

    report = DatabaseValidationReport(
        field_photo_records=field_photo_records,
        database_field_photos=database_field_photos,
        settings_records=settings_records,
        database_settings=database_settings,
        privacy_request_records=privacy_request_records,
        database_privacy_requests=database_privacy_requests,
        missing_paths=missing_paths,
    )
    mismatches = []
    if report.database_field_photos != report.field_photo_records:
        mismatches.append(f"field_photos={report.database_field_photos}/{report.field_photo_records}")
    if report.database_settings != report.settings_records:
        mismatches.append(f"settings={report.database_settings}/{report.settings_records}")
    if report.database_privacy_requests != report.privacy_request_records:
        mismatches.append(f"privacy_requests={report.database_privacy_requests}/{report.privacy_request_records}")
    if report.missing_paths:
        mismatches.append(f"missing_paths={len(report.missing_paths)}")
    if mismatches:
        raise ValueError("Walidacja DB nie powiodla sie: " + ", ".join(mismatches))
    return report


def migrate_json_to_database(
    *,
    root_dir: Path = ROOT_DIR,
    database_path: Path = config.DATABASE_PATH,
    require_backup: bool = True,
) -> JsonToDatabaseReport:
    root = root_dir.resolve()
    database = database_path if database_path.is_absolute() else root / database_path
    if require_backup:
        ensure_backup_snapshot(root)

    connection = connect_database(database)
    try:
        apply_migrations(connection)
        field_paths = field_photo_record_paths(root)
        privacy_paths = privacy_request_paths(root)
        with connection:
            for path in field_paths:
                record = read_json_object(path)
                require_existing_photo_files(root, path.parent, record)
                upsert_field_photo(connection, record)

            settings_records = upsert_settings(connection, root / config.SETTINGS_FILENAME)

            for path in privacy_paths:
                upsert_privacy_request(connection, read_json_object(path))

            validate_database_counts(
                connection,
                field_photo_records=len(field_paths),
                settings_records=settings_records,
                privacy_request_records=len(privacy_paths),
            )
    finally:
        connection.close()

    validate_database_against_json(root_dir=root, database_path=database)

    return JsonToDatabaseReport(
        database_path=database,
        field_photo_records=len(field_paths),
        migrated_field_photos=len(field_paths),
        settings_records=settings_records,
        migrated_settings=settings_records,
        privacy_request_records=len(privacy_paths),
        migrated_privacy_requests=len(privacy_paths),
    )

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config
from core.database import apply_migrations, connect_database, upsert_privacy_request

PRIVACY_REQUEST_STATUSES = {"new", "in_progress", "done", "rejected"}
DATABASE_PATH = Path(__file__).resolve().parent.parent / config.DATABASE_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_text(value: Any, max_len: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) > max_len:
        raise ValueError("Jedno z pól formularza jest zbyt długie.")
    return text


def _request_id(created_at: str, email: str) -> str:
    digest = hashlib.sha1(
        f"{created_at}:{email}:{secrets.token_urlsafe(12)}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:10]
    stamp = created_at.replace("-", "").replace(":", "").removesuffix("Z")
    return f"privacy_{stamp}_{digest}"


def _safe_request_id(value: Any) -> str:
    request_id = str(value or "").strip()
    if not request_id.startswith("privacy_") or "/" in request_id or "\\" in request_id or ".." in request_id:
        raise ValueError("Nieprawidłowy identyfikator zgłoszenia.")
    return request_id


def _normalize_status(value: Any) -> str:
    status = str(value or "new").strip()
    if status not in PRIVACY_REQUEST_STATUSES:
        raise ValueError("Nieprawidłowy status zgłoszenia.")
    return status


def _connection():
    connection = connect_database(DATABASE_PATH)
    apply_migrations(connection)
    return connection


def _ensure_request_fields(payload: dict[str, Any]) -> bool:
    changed = False
    if "status" not in payload:
        payload["status"] = "new"
        changed = True
    else:
        payload["status"] = _normalize_status(payload.get("status"))
    if "updated_at" not in payload:
        payload["updated_at"] = payload.get("created_at")
        changed = True
    if "handled_at" not in payload:
        payload["handled_at"] = payload.get("updated_at") if payload.get("status") in {"done", "rejected"} else None
        changed = True
    if "admin_note" not in payload:
        payload["admin_note"] = ""
        changed = True
    return changed


def _payload_from_row(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "email": row["email"],
        "target": row["target"],
        "reason": row["reason"],
        "updated_at": row["updated_at"],
        "handled_at": row["handled_at"],
        "admin_note": row["admin_note"],
    }
    _ensure_request_fields(payload)
    return payload


def create_privacy_request(fields: dict[str, Any]) -> dict[str, Any]:
    email = _safe_text(fields.get("email"), 180)
    target = _safe_text(fields.get("target"), 500)
    reason = _safe_text(fields.get("reason"), 4000)
    if not email or not target or not reason:
        raise ValueError("Uzupełnij e-mail, link albo identyfikator wpisu oraz opis żądania.")
    created_at = _now_iso()
    request_id = _request_id(created_at, email)
    payload = {
        "id": request_id,
        "created_at": created_at,
        "status": "new",
        "email": email,
        "target": target,
        "reason": reason,
        "updated_at": created_at,
        "handled_at": None,
        "admin_note": "",
    }
    connection = _connection()
    try:
        with connection:
            upsert_privacy_request(connection, payload)
    finally:
        connection.close()
    return {"status": "ok", "request_id": request_id}


def list_privacy_requests(*, status: Any = "all") -> list[dict[str, Any]]:
    status_filter = str(status or "all").strip()
    if status_filter != "all" and status_filter not in PRIVACY_REQUEST_STATUSES:
        raise ValueError("Nieprawidłowy filtr statusu zgłoszeń.")
    query = "SELECT * FROM privacy_requests"
    params: tuple[Any, ...] = ()
    if status_filter != "all":
        query += " WHERE status = ?"
        params = (status_filter,)
    query += " ORDER BY updated_at DESC, created_at DESC"
    connection = _connection()
    try:
        return [_payload_from_row(row) for row in connection.execute(query, params)]
    finally:
        connection.close()


def update_privacy_request(request_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    request_id = _safe_request_id(request_id)
    connection = _connection()
    try:
        row = connection.execute("SELECT * FROM privacy_requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            raise FileNotFoundError("Nie znaleziono zgłoszenia.")
        payload = _payload_from_row(row)
    finally:
        connection.close()
    _ensure_request_fields(payload)
    status = _normalize_status(fields.get("status", payload.get("status")))
    admin_note = _safe_text(fields.get("admin_note", payload.get("admin_note")), 4000)
    updated_at = _now_iso()
    payload["status"] = status
    payload["admin_note"] = admin_note
    payload["updated_at"] = updated_at
    payload["handled_at"] = updated_at if status in {"done", "rejected"} else None
    connection = _connection()
    try:
        with connection:
            upsert_privacy_request(connection, payload)
    finally:
        connection.close()
    return {"status": "ok", "request": payload}

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

MIN_PHOTO_EDIT_TOKEN_LENGTH = 8
MAX_PHOTO_EDIT_TOKEN_LENGTH = 80


def generate_photo_edit_token() -> str:
    return secrets.token_urlsafe(18)


def normalize_photo_edit_token(token: Any) -> str:
    normalized = str(token or "").replace("\x00", "").strip()
    if len(normalized) < MIN_PHOTO_EDIT_TOKEN_LENGTH:
        raise ValueError("Token edycji zdjęcia musi mieć co najmniej 8 znaków.")
    if len(normalized) > MAX_PHOTO_EDIT_TOKEN_LENGTH:
        raise ValueError("Token edycji zdjęcia może mieć maksymalnie 80 znaków.")
    return normalized


def new_photo_edit_token_hash(token: Any) -> dict[str, str]:
    normalized = normalize_photo_edit_token(token)
    salt = secrets.token_urlsafe(16)
    return {
        "edit_token_salt": salt,
        "edit_token_hash": _photo_edit_token_hash(normalized, salt),
    }


def verify_photo_edit_token(token: Any, salt: Any, stored_hash: Any) -> bool:
    salt_text = str(salt or "").strip()
    stored_hash_text = str(stored_hash or "").strip()
    if not salt_text or not stored_hash_text:
        return False
    return hmac.compare_digest(_photo_edit_token_hash(normalize_photo_edit_token(token), salt_text), stored_hash_text)


def _photo_edit_token_hash(token: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{token}".encode()).hexdigest()

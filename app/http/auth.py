import hashlib
import hmac
import os
import secrets
import time

from app import config


def admin_password() -> str | None:
    password = os.environ.get("WRECKSCANNER_ADMIN_PASSWORD", "").strip()
    if password:
        return password
    try:
        password = config.ADMIN_PASSWORD_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return password or None


def admin_enabled() -> bool:
    return admin_password() is not None


def admin_signature(payload: str, password: str) -> str:
    key = f"{config.ADMIN_SESSION_SECRET}:{password}".encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def make_admin_token(password: str) -> str:
    issued_at = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{issued_at}:{nonce}"
    return f"{payload}:{admin_signature(payload, password)}"


def valid_admin_token(token: str | None) -> bool:
    password = admin_password()
    if not password or not token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    issued_at, nonce, signature = parts
    try:
        issued = int(issued_at)
    except ValueError:
        return False
    now = int(time.time())
    if issued > now + config.ADMIN_SESSION_CLOCK_SKEW_SECONDS or now - issued > config.ADMIN_SESSION_SECONDS:
        return False
    payload = f"{issued_at}:{nonce}"
    expected = admin_signature(payload, password)
    return hmac.compare_digest(signature, expected)


def password_matches(candidate: str, password: str) -> bool:
    return hmac.compare_digest(candidate, password)

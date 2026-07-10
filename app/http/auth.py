import hashlib
import hmac
import os
import secrets
import time
from threading import Lock

from app import config

_ACTIVE_ADMIN_SESSIONS: dict[str, int] = {}
_ACTIVE_ADMIN_SESSIONS_LOCK = Lock()


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


def _session_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _prune_active_sessions(now: int) -> None:
    expired = [digest for digest, expires_at in _ACTIVE_ADMIN_SESSIONS.items() if expires_at < now]
    for digest in expired:
        _ACTIVE_ADMIN_SESSIONS.pop(digest, None)


def _register_admin_token(token: str, issued_at: int) -> None:
    with _ACTIVE_ADMIN_SESSIONS_LOCK:
        _prune_active_sessions(issued_at)
        while len(_ACTIVE_ADMIN_SESSIONS) >= config.ADMIN_MAX_ACTIVE_SESSIONS:
            oldest = min(_ACTIVE_ADMIN_SESSIONS, key=_ACTIVE_ADMIN_SESSIONS.get)
            _ACTIVE_ADMIN_SESSIONS.pop(oldest, None)
        _ACTIVE_ADMIN_SESSIONS[_session_digest(token)] = issued_at + config.ADMIN_SESSION_SECONDS


def revoke_admin_token(token: str | None) -> None:
    if not token:
        return
    with _ACTIVE_ADMIN_SESSIONS_LOCK:
        _ACTIVE_ADMIN_SESSIONS.pop(_session_digest(token), None)


def make_admin_token(password: str) -> str:
    issued = int(time.time())
    issued_at = str(issued)
    nonce = secrets.token_urlsafe(16)
    payload = f"{issued_at}:{nonce}"
    token = f"{payload}:{admin_signature(payload, password)}"
    _register_admin_token(token, issued)
    return token


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
    with _ACTIVE_ADMIN_SESSIONS_LOCK:
        _prune_active_sessions(now)
    if issued > now + config.ADMIN_SESSION_CLOCK_SKEW_SECONDS or now - issued > config.ADMIN_SESSION_SECONDS:
        return False
    payload = f"{issued_at}:{nonce}"
    expected = admin_signature(payload, password)
    if not hmac.compare_digest(signature, expected):
        return False
    digest = _session_digest(token)
    with _ACTIVE_ADMIN_SESSIONS_LOCK:
        return _ACTIVE_ADMIN_SESSIONS.get(digest, 0) >= now


def password_matches(candidate: str, password: str) -> bool:
    return hmac.compare_digest(candidate, password)

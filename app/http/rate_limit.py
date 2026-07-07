from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from app.http import responses as http_responses


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    methods: frozenset[str]
    exact_paths: frozenset[str]
    prefixes: tuple[str, ...]
    limit: int
    window_seconds: int
    message: str

    def matches(self, method: str, path: str) -> bool:
        method = method.upper()
        if method not in self.methods:
            return False
        return path in self.exact_paths or any(path.startswith(prefix) for prefix in self.prefixes)


_RULES = (
    RateLimitRule(
        name="admin-login",
        methods=frozenset({"POST"}),
        exact_paths=frozenset({"/api/admin/login"}),
        prefixes=(),
        limit=5,
        window_seconds=10 * 60,
        message="Zbyt wiele prób logowania. Spróbuj ponownie za chwilę.",
    ),
    RateLimitRule(
        name="public-photo-upload",
        methods=frozenset({"POST"}),
        exact_paths=frozenset({"/api/field-photos"}),
        prefixes=(),
        limit=30,
        window_seconds=60 * 60,
        message="Zbyt wiele zgłoszeń zdjęć z tego źródła. Spróbuj ponownie później.",
    ),
    RateLimitRule(
        name="owner-photo-actions",
        methods=frozenset({"POST", "PATCH"}),
        exact_paths=frozenset(
            {
                "/api/field-photos/owner-claim",
                "/api/field-photos/owner-submit",
                "/api/field-photos/owner-discard",
                "/api/field-photos/owner-delete",
            }
        ),
        prefixes=("/api/field-photos/",),
        limit=120,
        window_seconds=15 * 60,
        message="Zbyt wiele operacji na zdjęciach. Spróbuj ponownie za chwilę.",
    ),
    RateLimitRule(
        name="privacy-requests",
        methods=frozenset({"POST"}),
        exact_paths=frozenset({"/api/privacy-requests"}),
        prefixes=(),
        limit=10,
        window_seconds=60 * 60,
        message="Zbyt wiele zgłoszeń prywatności z tego źródła. Spróbuj ponownie później.",
    ),
    RateLimitRule(
        name="report-pdf",
        methods=frozenset({"POST"}),
        exact_paths=frozenset({"/api/field-photo-reports/report-pdf"}),
        prefixes=(),
        limit=12,
        window_seconds=15 * 60,
        message="Zbyt wiele prób generowania raportu. Spróbuj ponownie za chwilę.",
    ),
    RateLimitRule(
        name="geo-lookups",
        methods=frozenset({"GET", "POST"}),
        exact_paths=frozenset({"/api/address/reverse", "/api/cadastral/identify", "/api/inspect"}),
        prefixes=(),
        limit=180,
        window_seconds=10 * 60,
        message="Zbyt wiele zapytań mapowych. Spróbuj ponownie za chwilę.",
    ),
)

_BUCKETS: defaultdict[tuple[str, str], deque[float]] = defaultdict(deque)
_BUCKET_LOCK = Lock()
_CLIENT_ID_SAFE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_:")


def _safe_client_token(value: object) -> str:
    text = str(value or "").strip().split(",", 1)[0].strip()
    safe = "".join(char for char in text[:120] if char in _CLIENT_ID_SAFE_CHARS)
    return safe or "unknown"


def client_key(handler) -> str:
    for header in ("CF-Connecting-IP", "X-Forwarded-For"):
        value = _safe_client_token(handler.headers.get(header))
        if value != "unknown":
            return value
    client_address = getattr(handler, "client_address", ("unknown",))
    return _safe_client_token(client_address[0] if client_address else "unknown")


def matching_rule(method: str, path: str) -> RateLimitRule | None:
    for rule in _RULES:
        if rule.matches(method, path):
            return rule
    return None


def reject_limited(handler, method: str, path: str) -> bool:
    rule = matching_rule(method, path)
    if rule is None:
        return False

    now = time.monotonic()
    key = (rule.name, client_key(handler))
    with _BUCKET_LOCK:
        bucket = _BUCKETS[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= rule.limit:
            retry_after = max(1, int(round(rule.window_seconds - (now - bucket[0]))))
            http_responses.send_json(
                handler,
                429,
                {
                    "error": rule.message,
                    "retry_after_seconds": retry_after,
                },
                {"Retry-After": str(retry_after)},
            )
            return True
        bucket.append(now)
    return False

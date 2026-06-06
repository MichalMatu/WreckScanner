from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core import config, report_models
from core.wrecks_store import read_json, validate_wreck_id


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_package_id(package_id: str) -> str:
    if not re.fullmatch(r"report_\d{8}T\d{6}Z_[a-f0-9]{8}", str(package_id or "")):
        raise ValueError("Nieprawidłowy identyfikator pakietu zgłoszenia.")
    return package_id


def new_access_token() -> report_models.ReportPackageAccess:
    expires_at = _now_utc() + timedelta(seconds=config.PUBLIC_REPORT_PACKAGE_TOKEN_TTL_SECONDS)
    return report_models.ReportPackageAccess(token=secrets.token_urlsafe(24), expires_at=_iso(expires_at))


def report_package_asset(wreck_id: str, package_id: str, asset: str) -> tuple[Path, str]:
    wreck_id = validate_wreck_id(wreck_id)
    package_id = _validate_package_id(package_id)
    if asset == "zip":
        path = config.PRIVATE_REPORTS_DIR / wreck_id / f"{package_id}.zip"
        content_type = "application/zip"
    elif asset == "pdf":
        path = config.PRIVATE_REPORTS_DIR / wreck_id / f"{package_id}.pdf"
        content_type = "application/pdf"
    else:
        raise ValueError("Nieprawidłowy typ pliku pakietu zgłoszenia.")
    root = config.PRIVATE_REPORTS_DIR.resolve()
    resolved = path.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("Nieprawidłowa ścieżka pakietu zgłoszenia.")
    if not resolved.exists():
        raise FileNotFoundError("Nie znaleziono pakietu zgłoszenia.")
    return resolved, content_type


def public_report_package_asset(wreck_id: str, package_id: str, asset: str, token: str) -> tuple[Path, str]:
    path, content_type = report_package_asset(wreck_id, package_id, asset)
    access_path = config.PRIVATE_REPORTS_DIR / wreck_id / f"{package_id}.access.json"
    try:
        access = read_json(access_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise FileNotFoundError("Nie znaleziono publicznego dostępu do pakietu.") from exc
    if not isinstance(access, dict) or access.get("scope") != "public_clean_report":
        raise FileNotFoundError("Nie znaleziono publicznego dostępu do pakietu.")
    if not secrets.compare_digest(str(access.get("token") or ""), str(token or "")):
        raise FileNotFoundError("Nie znaleziono publicznego dostępu do pakietu.")
    expires_text = str(access.get("expires_at") or "").replace("Z", "+00:00")
    try:
        expires_at = datetime.fromisoformat(expires_text)
    except ValueError as exc:
        raise FileNotFoundError("Publiczny dostęp do pakietu wygasł.") from exc
    if expires_at < _now_utc():
        raise FileNotFoundError("Publiczny dostęp do pakietu wygasł.")
    return path, content_type

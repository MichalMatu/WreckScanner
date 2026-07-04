from __future__ import annotations

import re


def _validate_package_id(package_id: str) -> str:
    if not re.fullmatch(r"report_\d{8}T\d{6}Z_[a-f0-9]{8}", str(package_id or "")):
        raise ValueError("Nieprawidłowy identyfikator pakietu zgłoszenia.")
    return package_id


def report_package_download_name(package_id: str, asset: str) -> str:
    package_id = _validate_package_id(package_id)
    if asset not in {"zip", "pdf"}:
        raise ValueError("Nieprawidłowy typ pliku pakietu zgłoszenia.")
    stamp = package_id.removeprefix("report_").split("_", 1)[0].replace("T", "_").removesuffix("Z")
    return f"raport_{stamp}.{asset}"

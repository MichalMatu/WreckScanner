from __future__ import annotations

import re


def _validate_report_id(report_id: str) -> str:
    if not re.fullmatch(r"report_\d{8}T\d{6}Z_[a-f0-9]{8}", str(report_id or "")):
        raise ValueError("Nieprawidłowy identyfikator raportu.")
    return report_id


def report_pdf_download_name(report_id: str) -> str:
    report_id = _validate_report_id(report_id)
    stamp = report_id.removeprefix("report_").split("_", 1)[0].replace("T", "_").removesuffix("Z")
    return f"raport_{stamp}.pdf"

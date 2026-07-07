from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any

from core.json_io import write_json_atomic
from core.map_crops import save_location_crops


def _write_json(path: Path, payload: Any) -> None:
    write_json_atomic(path, payload)


def _location_evidence_id(prefix: str, lat: float, lon: float, created_at: str) -> str:
    payload = f"{prefix}:{lat:.8f}:{lon:.8f}:{created_at}:{secrets.token_urlsafe(8)}"
    digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()[:14]
    return f"{prefix}_{digest}"


def save_report_evidence(
    *,
    lat: float,
    lon: float,
    record_dir: Path,
    created_at: str,
    crop_m: Any,
    links: dict[str, str],
) -> dict[str, Any]:
    evidence_id_value = _location_evidence_id("report", lat, lon, created_at)
    evidence_rel = f"evidence/{evidence_id_value}"
    evidence_dir = record_dir / evidence_rel
    crops, metadata = save_location_crops(lat, lon, evidence_dir, crop_m=crop_m)
    labels = [crop["label"] for crop in crops]
    evidence = {
        "id": evidence_id_value,
        "created_at": created_at,
        "lat": lat,
        "lon": lon,
        "labels_present": labels,
        "path": evidence_rel,
        "crops": crops,
        "links": links,
        "source": "report_pdf",
        "crop_m": float(crop_m),
    }
    _write_json(evidence_dir / "links.json", links)
    _write_json(evidence_dir / "metadata.json", metadata)
    _write_json(
        evidence_dir / "report_pdf.json",
        {
            "source": "report_pdf",
            "created_at": created_at,
            "lat": lat,
            "lon": lon,
            "links": links,
            "crop_m": float(crop_m),
            "labels_present": labels,
        },
    )
    return evidence


def first_last_year(labels: list[Any]) -> tuple[int | None, int | None]:
    years = sorted(int(label) for label in labels if str(label).isdigit())
    if not years:
        return None, None
    return years[0], years[-1]

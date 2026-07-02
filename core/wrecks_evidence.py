from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any

from core.map_crops import save_location_crops
from core.wrecks_store import write_json


def _location_evidence_id(prefix: str, lat: float, lon: float, created_at: str) -> str:
    payload = f"{prefix}:{lat:.8f}:{lon:.8f}:{created_at}:{secrets.token_urlsafe(8)}"
    digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()[:14]
    return f"{prefix}_{digest}"


def save_location_evidence(
    *,
    lat: float,
    lon: float,
    record_dir: Path,
    created_at: str,
    crop_m: Any,
    links: dict[str, str],
    source: str,
    id_prefix: str,
) -> dict[str, Any]:
    evidence_id_value = _location_evidence_id(id_prefix, lat, lon, created_at)
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
        "source": source,
        "crop_m": float(crop_m),
    }
    write_json(evidence_dir / "links.json", links)
    write_json(evidence_dir / "metadata.json", metadata)
    write_json(
        evidence_dir / f"{source}.json",
        {
            "source": source,
            "created_at": created_at,
            "lat": lat,
            "lon": lon,
            "links": links,
            "crop_m": float(crop_m),
            "labels_present": labels,
        },
    )
    return evidence


def save_report_evidence(
    *,
    lat: float,
    lon: float,
    record_dir: Path,
    created_at: str,
    crop_m: Any,
    links: dict[str, str],
) -> dict[str, Any]:
    return save_location_evidence(
        lat=lat,
        lon=lon,
        record_dir=record_dir,
        created_at=created_at,
        crop_m=crop_m,
        links=links,
        source="report_package",
        id_prefix="report",
    )


def first_last_year(labels: list[Any]) -> tuple[int | None, int | None]:
    years = sorted(int(label) for label in labels if str(label).isdigit())
    if not years:
        return None, None
    return years[0], years[-1]

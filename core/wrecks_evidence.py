from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
from pathlib import Path
from typing import Any

from core.map_crops import save_scan_crops
from core.wrecks_store import write_json


def evidence_id(candidate: dict[str, Any], metadata: dict[str, Any]) -> str:
    payload = {
        "lat": candidate.get("lat"),
        "lon": candidate.get("lon"),
        "score": candidate.get("score"),
        "rank": candidate.get("rank"),
        "labels_present": candidate.get("labels_present"),
        "bbox_4326": metadata.get("bbox_4326"),
        "years": metadata.get("years"),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()[:14]


def _manual_evidence_id(lat: float, lon: float, created_at: str) -> str:
    payload = f"{lat:.8f}:{lon:.8f}:{created_at}:{secrets.token_urlsafe(8)}"
    digest = hashlib.sha1(payload.encode("utf-8"), usedforsecurity=False).hexdigest()[:14]
    return f"manual_{digest}"


def _crop_year_from_name(path: Path) -> str:
    match = re.match(r"cand_\d+_(.+)\.jpe?g$", path.name, flags=re.IGNORECASE)
    return match.group(1) if match else path.stem


def copy_candidate_crops(rank: int, analysis_dir: Path, evidence_dir: Path) -> list[dict[str, str]]:
    src_dir = analysis_dir / "crops"
    prefix = f"cand_{rank - 1:03d}_"
    copied: list[dict[str, str]] = []
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.glob(f"{prefix}*.jpg")):
        year = _crop_year_from_name(src)
        dst_name = f"{year}.jpg"
        dst = evidence_dir / dst_name
        shutil.copy2(src, dst)
        copied.append({"label": year, "file": dst_name})
    if not copied:
        raise FileNotFoundError(f"Brak miniatur dla kandydata #{rank} w {src_dir}.")
    return copied


def save_manual_evidence(
    *,
    lat: float,
    lon: float,
    data_dir: Path,
    record_dir: Path,
    created_at: str,
    crop_m: Any,
    links: dict[str, str],
) -> dict[str, Any]:
    evidence_id_value = _manual_evidence_id(lat, lon, created_at)
    evidence_rel = f"evidence/{evidence_id_value}"
    evidence_dir = record_dir / evidence_rel
    crops, metadata = save_scan_crops(lat, lon, data_dir, evidence_dir, crop_m=crop_m)
    labels = [crop["label"] for crop in crops]
    evidence = {
        "id": evidence_id_value,
        "created_at": created_at,
        "rank": None,
        "score": None,
        "lat": lat,
        "lon": lon,
        "labels_present": labels,
        "path": evidence_rel,
        "crops": crops,
        "links": links,
        "source": "manual_inspection",
        "crop_m": float(crop_m),
    }
    write_json(evidence_dir / "links.json", links)
    write_json(evidence_dir / "metadata.json", metadata)
    write_json(
        evidence_dir / "manual_inspection.json",
        {
            "source": "manual_inspection",
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

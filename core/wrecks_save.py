from __future__ import annotations

from pathlib import Path
from typing import Any

from core import config
from core.photo_privacy import REVIEW_STATUSES, is_approved
from core.photo_privacy import now_iso as privacy_now_iso
from core.wrecks_catalog import find_existing_record
from core.wrecks_evidence import first_last_year, save_manual_evidence
from core.wrecks_identity import links, now_iso, validate_coordinates, wreck_id
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_public import wreck_summary
from core.wrecks_rendering import render_record_html
from core.wrecks_store import write_json


def _render_record_html(record: dict[str, Any], record_dir: Path) -> None:
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    render_record_html(record, record_dir)


def save_manual_wreck(
    lat: Any,
    lon: Any,
    wrecks_dir: Path,
    *,
    crop_m: Any = config.REVIEW_CROP_M,
    public_review_status: str = "approved",
    submission_owner: str | None = None,
) -> dict[str, Any]:
    lat_f, lon_f = validate_coordinates(lat, lon)
    if public_review_status not in REVIEW_STATUSES:
        raise ValueError("Nieprawidłowy status przeglądu sprawy.")
    existing, distance_m = find_existing_record(wrecks_dir, lat_f, lon_f)
    if existing:
        record_changed = False
        if not is_approved(existing) and public_review_status == "approved":
            existing["public_review_status"] = "approved"
            existing["reviewed_at"] = privacy_now_iso()
            record_changed = True
        record_dir = wrecks_dir / existing["id"]
        if record_changed:
            write_json(record_dir / "record.json", existing)
        _render_record_html(existing, record_dir)
        return {
            "status": "ok",
            "created": False,
            "evidence_created": False,
            "dedupe_distance_m": round(distance_m, 2) if distance_m is not None else None,
            "wreck": wreck_summary(existing),
        }

    created_at = now_iso()
    map_links = links(lat_f, lon_f)
    new_wreck_id = wreck_id(lat_f, lon_f)
    record_dir = wrecks_dir / new_wreck_id
    evidence = save_manual_evidence(
        lat=lat_f,
        lon=lon_f,
        record_dir=record_dir,
        created_at=created_at,
        crop_m=crop_m,
        links=map_links,
    )
    labels = [str(label) for label in evidence.get("labels_present") or []]
    first_seen, last_seen = first_last_year(labels)
    record = {
        "id": new_wreck_id,
        "status": "manual",
        "lat": lat_f,
        "lon": lon_f,
        "created_at": created_at,
        "updated_at": created_at,
        "labels_present": labels,
        "first_seen_year": first_seen,
        "last_seen_year": last_seen,
        "latest_evidence": evidence,
        "links": map_links,
        "evidences": [evidence],
        "source": "manual_inspection",
        "public_review_status": public_review_status,
        "reviewed_at": privacy_now_iso() if public_review_status == "approved" else None,
        "reviewed_by": "admin" if public_review_status == "approved" else None,
        "submission_owner": submission_owner,
    }

    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)

    return {
        "status": "ok",
        "created": True,
        "evidence_created": True,
        "dedupe_distance_m": None,
        "wreck": wreck_summary(record),
    }

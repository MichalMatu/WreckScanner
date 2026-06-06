from __future__ import annotations

from pathlib import Path
from typing import Any

from core import config
from core.photo_privacy import REVIEW_STATUSES, is_approved
from core.photo_privacy import now_iso as privacy_now_iso
from core.wrecks_catalog import find_existing_record
from core.wrecks_evidence import copy_candidate_crops, evidence_id, first_last_year, save_manual_evidence
from core.wrecks_identity import links, now_iso, validate_coordinates, wreck_id
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_public import wreck_summary
from core.wrecks_rendering import render_record_html
from core.wrecks_store import read_json, write_json


def _candidate_by_rank(candidates: list[dict[str, Any]], rank: int) -> dict[str, Any]:
    for candidate in candidates:
        if int(candidate.get("rank") or 0) == rank:
            return candidate
    raise ValueError(f"Brak kandydata o numerze #{rank}. Uruchom aktualną analizę ponownie.")


def _render_record_html(record: dict[str, Any], record_dir: Path) -> None:
    if migrate_wreck_record(record_dir, record):
        write_json(record_dir / "record.json", record)
    render_record_html(record, record_dir)


def save_manual_wreck(
    lat: Any,
    lon: Any,
    data_dir: Path,
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
        data_dir=data_dir,
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
        "best_score": 0.0,
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


def save_wreck_from_rank(
    rank: int,
    analysis_dir: Path,
    data_dir: Path,
    wrecks_dir: Path,
    *,
    public_review_status: str = "approved",
    submission_owner: str | None = None,
) -> dict[str, Any]:
    if public_review_status not in REVIEW_STATUSES:
        raise ValueError("Nieprawidłowy status przeglądu sprawy.")
    candidates_path = analysis_dir / "candidates.json"
    metadata_path = data_dir / "metadata.json"
    if not candidates_path.exists():
        raise FileNotFoundError("Brak aktualnych kandydatów. Najpierw uruchom analizę.")
    if not metadata_path.exists():
        raise FileNotFoundError("Brak metadata.json. Najpierw pobierz i przeanalizuj obszar.")

    candidates = read_json(candidates_path)
    metadata = read_json(metadata_path)
    if not isinstance(candidates, list):
        raise ValueError("Nieprawidłowy format candidates.json.")

    candidate = _candidate_by_rank(candidates, rank)
    lat = candidate.get("lat")
    lon = candidate.get("lon")
    if lat is None or lon is None:
        raise ValueError(f"Kandydat #{rank} nie ma współrzędnych GPS.")
    lat = float(lat)
    lon = float(lon)

    existing, distance_m = find_existing_record(wrecks_dir, lat, lon)
    created_record = existing is None
    if existing:
        record = existing
        new_wreck_id = record["id"]
        if not is_approved(record) and public_review_status == "approved":
            record["public_review_status"] = "approved"
            record["reviewed_at"] = privacy_now_iso()
    else:
        new_wreck_id = wreck_id(lat, lon)
        record = {
            "id": new_wreck_id,
            "status": "confirmed",
            "lat": lat,
            "lon": lon,
            "created_at": now_iso(),
            "updated_at": None,
            "best_score": 0.0,
            "labels_present": [],
            "first_seen_year": None,
            "last_seen_year": None,
            "latest_evidence": None,
            "links": links(lat, lon),
            "evidences": [],
            "public_review_status": public_review_status,
            "reviewed_at": privacy_now_iso() if public_review_status == "approved" else None,
            "reviewed_by": "admin" if public_review_status == "approved" else None,
            "submission_owner": submission_owner,
        }

    record_dir = wrecks_dir / new_wreck_id
    new_evidence_id = evidence_id(candidate, metadata)
    evidence_rel = f"evidence/{new_evidence_id}"
    evidence_dir = record_dir / evidence_rel
    evidence_exists = any(item.get("id") == new_evidence_id for item in record.get("evidences") or [])
    evidence_created = not evidence_exists

    if evidence_created:
        crops = copy_candidate_crops(rank, analysis_dir, evidence_dir)
        map_links = links(lat, lon)
        write_json(evidence_dir / "candidate.json", candidate)
        write_json(evidence_dir / "metadata.json", metadata)
        write_json(evidence_dir / "links.json", map_links)
        evidence = {
            "id": new_evidence_id,
            "created_at": now_iso(),
            "rank": rank,
            "score": candidate.get("score"),
            "lat": lat,
            "lon": lon,
            "labels_present": candidate.get("labels_present") or [],
            "path": evidence_rel,
            "crops": crops,
            "links": map_links,
        }
        record.setdefault("evidences", []).append(evidence)

    best_score = max(float(record.get("best_score") or 0.0), float(candidate.get("score") or 0.0))
    record["best_score"] = best_score
    if float(candidate.get("score") or 0.0) >= best_score:
        record["lat"] = lat
        record["lon"] = lon
        record["links"] = links(lat, lon)
    labels = sorted({str(label) for item in record.get("evidences") or [] for label in item.get("labels_present", [])})
    first_seen, last_seen = first_last_year(labels)
    record["labels_present"] = labels
    record["first_seen_year"] = first_seen
    record["last_seen_year"] = last_seen
    record["latest_evidence"] = (record.get("evidences") or [])[-1] if record.get("evidences") else None
    record["updated_at"] = now_iso()

    write_json(record_dir / "record.json", record)
    _render_record_html(record, record_dir)

    return {
        "status": "ok",
        "created": created_record,
        "evidence_created": evidence_created,
        "dedupe_distance_m": round(distance_m, 2) if distance_m is not None else None,
        "wreck": wreck_summary(record),
    }

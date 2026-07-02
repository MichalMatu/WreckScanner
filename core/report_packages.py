from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import config, report_assets, report_mail, report_models, report_pdf, report_zip, wrecks_store
from core.wrecks import render_wreck_record_html
from core.wrecks_evidence import first_last_year, save_report_evidence
from core.wrecks_identity import links as location_links
from core.wrecks_identity import validate_coordinates


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_id(wreck_id: str, fields: dict[str, str]) -> str:
    stamp = _now_utc().strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(
        f"{wreck_id}:{fields['location_description']}:{stamp}:{secrets.token_urlsafe(8)}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:8]
    return f"report_{stamp}_{digest}"


def _append_report_history(
    record: dict[str, Any],
    record_dir: Path,
    *,
    package_id: str,
    public: bool,
    photo_count: int,
) -> None:
    history = record.get("report_history")
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "package_id": package_id,
            "created_at": _iso(_now_utc()),
            "public": public,
            "photo_count": int(photo_count),
        }
    )
    record["report_history"] = history[-50:]
    record["updated_at"] = _iso(_now_utc())
    wrecks_store.write_json(record_dir / "record.json", record)


def _append_report_evidence(record: dict[str, Any], record_dir: Path) -> dict[str, Any]:
    lat, lon = validate_coordinates(record.get("lat"), record.get("lon"))
    created_at = _iso(_now_utc())
    map_links = record.get("links") if isinstance(record.get("links"), dict) else location_links(lat, lon)
    evidence = save_report_evidence(
        lat=lat,
        lon=lon,
        record_dir=record_dir,
        created_at=created_at,
        crop_m=config.REVIEW_CROP_M,
        links=map_links,
    )
    evidences = record.get("evidences") if isinstance(record.get("evidences"), list) else []
    evidences.append(evidence)
    labels = [str(label) for label in evidence.get("labels_present") or []]
    first_seen, last_seen = first_last_year(labels)
    record["evidences"] = evidences
    record["latest_evidence"] = evidence
    record["labels_present"] = labels
    record["first_seen_year"] = first_seen
    record["last_seen_year"] = last_seen
    record["links"] = map_links
    record["updated_at"] = created_at
    wrecks_store.write_json(record_dir / "record.json", record)
    return evidence


def create_report_package(
    wreck_id: str,
    fields: dict[str, str],
    photos: list[report_models.ReportPhotoUpload],
    wrecks_dir: Path,
) -> dict[str, Any]:
    fields = report_models.validate_report_fields(fields)
    prepared_photos = report_models.prepare_report_photos(photos)
    record_dir = wrecks_store.record_dir_for(wreck_id, wrecks_dir)
    record = wrecks_store.read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    evidence = _append_report_evidence(record, record_dir)
    render_wreck_record_html(record, record_dir)
    subject, mail_body = report_mail.build_mail_draft(record, evidence, fields)

    package_id = _package_id(wreck_id, fields)
    reports_dir = config.PRIVATE_REPORTS_DIR / str(record["id"])
    package_dir = reports_dir / package_id
    originals_dir = package_dir / "oryginalne_zdjecia"
    optimized_dir = package_dir / "zdjecia_do_maila"
    zip_path = reports_dir / f"{package_id}.zip"
    pdf_path = reports_dir / f"{package_id}.pdf"
    originals_dir.mkdir(parents=True, exist_ok=False)
    optimized_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    for photo in prepared_photos:
        (originals_dir / photo.original_name).write_bytes(photo.original_data)
        (optimized_dir / photo.optimized_name).write_bytes(photo.optimized_data)

    report_zip.write_admin_zip(
        zip_path,
        record_dir,
        record,
        evidence,
        config.REPORT_RECIPIENT,
        subject,
        mail_body,
        prepared_photos,
    )
    report_pdf.write_report_pdf(
        pdf_path,
        record=record,
        evidence=evidence,
        record_dir=record_dir,
        recipient=config.REPORT_RECIPIENT,
        subject=subject,
        mail_body=mail_body,
        photos=prepared_photos,
    )
    _append_report_history(record, record_dir, package_id=package_id, public=False, photo_count=len(prepared_photos))
    return {
        "status": "ok",
        "recipient": config.REPORT_RECIPIENT,
        "subject": subject,
        "body": mail_body,
        "package_id": package_id,
        "zip_url": f"/api/report-packages/{record['id']}/{package_id}/zip",
        "pdf_url": f"/api/report-packages/{record['id']}/{package_id}/pdf",
        "photo_count": len(prepared_photos),
        "zip_size_bytes": zip_path.stat().st_size,
        "pdf_size_bytes": pdf_path.stat().st_size,
    }


def create_public_report_package(
    wreck_id: str,
    fields: dict[str, str],
    photos: list[report_models.ReportPhotoUpload],
    wrecks_dir: Path,
) -> dict[str, Any]:
    fields = report_models.validate_report_fields(fields)
    prepared_photos = report_models.prepare_report_photos(photos)
    record_dir = wrecks_store.record_dir_for(wreck_id, wrecks_dir)
    record = wrecks_store.read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    evidence = _append_report_evidence(record, record_dir)
    render_wreck_record_html(record, record_dir)
    subject, mail_body = report_mail.build_mail_draft(record, evidence, fields)

    package_id = _package_id(wreck_id, fields)
    reports_dir = config.PRIVATE_REPORTS_DIR / str(record["id"])
    package_dir = reports_dir / package_id
    optimized_dir = package_dir / "zdjecia_do_maila"
    zip_path = reports_dir / f"{package_id}.zip"
    pdf_path = reports_dir / f"{package_id}.pdf"
    access_path = reports_dir / f"{package_id}.access.json"
    optimized_dir.mkdir(parents=True, exist_ok=False)
    reports_dir.mkdir(parents=True, exist_ok=True)

    for photo in prepared_photos:
        (optimized_dir / photo.optimized_name).write_bytes(photo.optimized_data)

    report_zip.write_public_zip(
        zip_path,
        record_dir,
        record,
        evidence,
        config.REPORT_RECIPIENT,
        subject,
        mail_body,
        prepared_photos,
    )
    report_pdf.write_report_pdf(
        pdf_path,
        record=record,
        evidence=evidence,
        record_dir=record_dir,
        recipient=config.REPORT_RECIPIENT,
        subject=subject,
        mail_body=mail_body,
        photos=prepared_photos,
    )
    _append_report_history(record, record_dir, package_id=package_id, public=True, photo_count=len(prepared_photos))
    access = report_assets.new_access_token()
    wrecks_store.write_json(
        access_path,
        {
            "package_id": package_id,
            "token": access.token,
            "expires_at": access.expires_at,
            "created_at": _iso(_now_utc()),
            "scope": "public_clean_report",
        },
    )
    token_query = f"?token={access.token}"
    return {
        "status": "ok",
        "recipient": config.REPORT_RECIPIENT,
        "subject": subject,
        "body": mail_body,
        "package_id": package_id,
        "zip_url": f"/api/public-report-packages/{record['id']}/{package_id}/zip{token_query}",
        "pdf_url": f"/api/public-report-packages/{record['id']}/{package_id}/pdf{token_query}",
        "expires_at": access.expires_at,
        "photo_count": len(prepared_photos),
        "zip_size_bytes": zip_path.stat().st_size,
        "pdf_size_bytes": pdf_path.stat().st_size,
    }

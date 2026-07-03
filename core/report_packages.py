from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from core import config, report_assets, report_mail, report_models, report_pdf, report_zip, wrecks_store
from core.photo_privacy import is_approved
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


def _build_report_evidence(record: dict[str, Any], evidence_base_dir: Path) -> dict[str, Any]:
    lat, lon = validate_coordinates(record.get("lat"), record.get("lon"))
    map_links = record.get("links") if isinstance(record.get("links"), dict) else location_links(lat, lon)
    return save_report_evidence(
        lat=lat,
        lon=lon,
        record_dir=evidence_base_dir,
        created_at=_iso(_now_utc()),
        crop_m=config.REVIEW_CROP_M,
        links=map_links,
    )


def _record_with_report_evidence(record: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    report_record = dict(record)
    evidences = record.get("evidences") if isinstance(record.get("evidences"), list) else []
    labels = [str(label) for label in evidence.get("labels_present") or []]
    first_seen, last_seen = first_last_year(labels)
    report_record["evidences"] = [*evidences, evidence]
    report_record["latest_evidence"] = evidence
    report_record["labels_present"] = labels
    report_record["first_seen_year"] = first_seen
    report_record["last_seen_year"] = last_seen
    report_record["links"] = evidence.get("links") or record.get("links") or {}
    report_record["updated_at"] = evidence.get("created_at")
    return report_record


def _approved_photo_count(record: dict[str, Any]) -> int:
    photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    return sum(
        1
        for photo in photos
        if isinstance(photo, dict)
        and is_approved(photo)
        and (photo.get("public_image_file") or photo.get("public_thumb_file"))
    )


def _download_payload(
    *,
    package_id: str,
    recipient: str,
    subject: str,
    mail_body: str,
    photo_count: int,
    zip_bytes: bytes,
    pdf_bytes: bytes,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "recipient": recipient,
        "subject": subject,
        "body": mail_body,
        "package_id": package_id,
        "zip_filename": report_assets.report_package_download_name(package_id, "zip"),
        "pdf_filename": report_assets.report_package_download_name(package_id, "pdf"),
        "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "photo_count": photo_count,
        "zip_size_bytes": len(zip_bytes),
        "pdf_size_bytes": len(pdf_bytes),
    }


def _create_report_package(
    wreck_id: str,
    fields: dict[str, str],
    wrecks_dir: Path,
    *,
    public: bool,
) -> dict[str, Any]:
    fields = report_models.validate_report_fields(fields)
    record_dir = wrecks_store.record_dir_for(wreck_id, wrecks_dir)
    record = wrecks_store.read_json(record_dir / "record.json")
    if not isinstance(record, dict):
        raise ValueError("Nieprawidłowy format record.json.")
    package_id = _package_id(wreck_id, fields)

    with TemporaryDirectory(prefix=f"{package_id}_") as work_dir_name:
        evidence_base_dir = Path(work_dir_name)
        evidence = _build_report_evidence(record, evidence_base_dir)
        report_record = _record_with_report_evidence(record, evidence)
        subject, mail_body = report_mail.build_mail_draft(report_record, evidence, fields)
        if public:
            zip_bytes = report_zip.build_public_zip(
                record_dir,
                evidence_base_dir,
                report_record,
                evidence,
                config.REPORT_RECIPIENT,
                subject,
                mail_body,
            )
        else:
            zip_bytes = report_zip.build_admin_zip(
                record_dir,
                evidence_base_dir,
                report_record,
                evidence,
                config.REPORT_RECIPIENT,
                subject,
                mail_body,
            )
        pdf_bytes = report_pdf.build_report_pdf(
            record=report_record,
            evidence=evidence,
            record_dir=record_dir,
            evidence_base_dir=evidence_base_dir,
            recipient=config.REPORT_RECIPIENT,
            subject=subject,
            mail_body=mail_body,
        )

    return _download_payload(
        package_id=package_id,
        recipient=config.REPORT_RECIPIENT,
        subject=subject,
        mail_body=mail_body,
        photo_count=_approved_photo_count(report_record),
        zip_bytes=zip_bytes,
        pdf_bytes=pdf_bytes,
    )


def create_report_package(
    wreck_id: str,
    fields: dict[str, str],
    wrecks_dir: Path,
) -> dict[str, Any]:
    return _create_report_package(wreck_id, fields, wrecks_dir, public=False)


def create_public_report_package(
    wreck_id: str,
    fields: dict[str, str],
    wrecks_dir: Path,
) -> dict[str, Any]:
    return _create_report_package(wreck_id, fields, wrecks_dir, public=True)

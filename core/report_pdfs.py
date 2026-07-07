from __future__ import annotations

import base64
import hashlib
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from core import config, report_assets, report_mail, report_models, report_pdf
from core.field_photo_metadata import (
    grouped_vehicle_insurance_checked_at,
    grouped_vehicle_insurance_status,
    vehicle_insurance_checked_at_from_record,
    vehicle_insurance_status_from_record,
)
from core.field_photos import FIELD_PHOTO_ID_RE, field_photo_record_dir, load_field_photo_record
from core.geo import external_map_links
from core.map_crops import validate_crop_m
from core.photo_privacy import is_approved, safe_child
from core.report_evidence import first_last_year, save_report_evidence

REPORT_PARCEL_KEYS = (
    "parcel_number",
    "parcel_id",
    "district",
    "municipality",
    "county",
    "voivodeship",
    "area_ha",
    "registry_group",
    "land_use",
    "contour",
    "published_at",
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _report_id(source_id: str, fields: dict[str, str]) -> str:
    stamp = _now_utc().strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(
        f"{source_id}:{fields['location_description']}:{stamp}:{secrets.token_urlsafe(8)}".encode(),
        usedforsecurity=False,
    ).hexdigest()[:8]
    return f"report_{stamp}_{digest}"


def _report_crop_m(fields: dict[str, str]) -> float:
    return validate_crop_m(fields.get("crop_m") or config.REVIEW_CROP_M)


def _report_context_text(value: Any, *, max_len: int = 240) -> str:
    return str(value or "").replace("\x00", "").strip()[:max_len]


def _normalize_report_parcel(parcel: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(parcel, dict):
        return {}
    normalized: dict[str, str] = {}
    for key in REPORT_PARCEL_KEYS:
        value = _report_context_text(parcel.get(key), max_len=240)
        if value:
            normalized[key] = value
    return normalized


def _build_report_evidence(record: dict[str, Any], evidence_base_dir: Path, *, crop_m: float) -> dict[str, Any]:
    lat = _float_coordinate(record.get("lat"), "lat")
    lon = _float_coordinate(record.get("lon"), "lon")
    map_links = record.get("links") if isinstance(record.get("links"), dict) else external_map_links(lat, lon)
    return save_report_evidence(
        lat=lat,
        lon=lon,
        record_dir=evidence_base_dir,
        created_at=_iso(_now_utc()),
        crop_m=crop_m,
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


def _field_photo_record_dir(photo_id: Any, field_photos_dir: Path) -> Path:
    photo_id_text = str(photo_id or "").strip()
    if not FIELD_PHOTO_ID_RE.fullmatch(photo_id_text):
        raise ValueError("Nieprawidłowy identyfikator zdjęcia terenowego.")
    return field_photo_record_dir(photo_id_text, field_photos_dir)


def _field_photo_records(photo_ids: list[Any], field_photos_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    seen: set[str] = set()
    for raw_photo_id in photo_ids:
        photo_id = str(raw_photo_id or "").strip()
        if not photo_id or photo_id in seen:
            continue
        seen.add(photo_id)
        record_dir = _field_photo_record_dir(photo_id, field_photos_dir)
        record = load_field_photo_record(photo_id, field_photos_dir)
        if not isinstance(record, dict) or str(record.get("id") or "") != photo_id:
            raise ValueError("Nieprawidłowy rekord zdjęcia terenowego.")
        if not is_approved(record):
            raise ValueError("Raport można wygenerować tylko z zatwierdzonych zdjęć terenowych.")
        if (
            str(record.get("issue_type") or config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE)
            != config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE
        ):
            raise ValueError("Raport pojazdu można wygenerować tylko ze zdjęć pojazdów.")
        records.append((record_dir, record))
    if not records:
        raise ValueError("Wybierz co najmniej jedno zdjęcie terenowe do raportu.")
    return records


def _copy_public_field_photo(record_dir: Path, record: dict[str, Any], report_root: Path) -> dict[str, Any]:
    photo_id = str(record.get("id") or "")
    output_dir = report_root / "photos" / photo_id
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for key, file_name in (("public_image_file", "public.jpg"), ("public_thumb_file", "public_thumb.jpg")):
        source = safe_child(record_dir, record.get(key))
        if not source.exists():
            raise FileNotFoundError("Brak publicznej kopii zdjęcia terenowego.")
        destination = output_dir / file_name
        shutil.copy2(source, destination)
        copied[key] = f"photos/{photo_id}/{file_name}"
    return {
        "id": photo_id,
        "created_at": record.get("created_at"),
        "original_filename": record.get("original_filename"),
        "content_type": "image/jpeg",
        "format": "JPEG",
        "size_bytes": record.get("size_bytes"),
        "image_width": record.get("image_width"),
        "image_height": record.get("image_height"),
        "issue_type": config.DEFAULT_FIELD_PHOTO_ISSUE_TYPE,
        "vehicle_insurance_status": vehicle_insurance_status_from_record(record),
        "vehicle_insurance_checked_at": vehicle_insurance_checked_at_from_record(record),
        "captured_at": record.get("captured_at"),
        "public_review_status": record.get("public_review_status"),
        "redactions": record.get("redactions") or [],
        "reviewed_at": record.get("reviewed_at"),
        "public_width": record.get("public_width"),
        "public_height": record.get("public_height"),
        **copied,
    }


def _float_coordinate(value: Any, label: str) -> float:
    try:
        coord = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nieprawidłowa wartość {label}.") from exc
    if not (-90 <= coord <= 90) and label == "lat":
        raise ValueError("Nieprawidłowa szerokość geograficzna.")
    if not (-180 <= coord <= 180) and label == "lon":
        raise ValueError("Nieprawidłowa długość geograficzna.")
    return coord


def _field_photo_report_record(
    *,
    photo_records: list[tuple[Path, dict[str, Any]]],
    lat: Any,
    lon: Any,
    parcel: dict[str, Any] | None = None,
    parcel_error: Any = "",
    report_root: Path,
) -> dict[str, Any]:
    lat_float = _float_coordinate(lat, "lat")
    lon_float = _float_coordinate(lon, "lon")
    safe_parcel = _normalize_report_parcel(parcel)
    safe_parcel_error = _report_context_text(parcel_error, max_len=500)
    links = external_map_links(lat_float, lon_float)
    attached_photos = [
        _copy_public_field_photo(record_dir, record, report_root) for record_dir, record in photo_records
    ]
    digest = hashlib.sha1(
        ":".join(str(photo.get("id") or "") for _, photo in photo_records).encode(),
        usedforsecurity=False,
    ).hexdigest()[:12]
    return {
        "id": f"field_photo_group_{digest}",
        "status": "field_photo_group",
        "vehicle_insurance_status": grouped_vehicle_insurance_status([record for _, record in photo_records]),
        "vehicle_insurance_checked_at": grouped_vehicle_insurance_checked_at([record for _, record in photo_records]),
        "lat": lat_float,
        "lon": lon_float,
        "labels_present": [],
        "first_seen_year": None,
        "last_seen_year": None,
        "links": links,
        "parcel": safe_parcel,
        "parcel_error": "" if safe_parcel else safe_parcel_error,
        "evidences": [],
        "attached_photos": attached_photos,
    }


def _download_payload(
    *,
    report_id: str,
    recipient: str,
    subject: str,
    photo_count: int,
    pdf_bytes: bytes,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "recipient": recipient,
        "subject": subject,
        "report_id": report_id,
        "pdf_filename": report_assets.report_pdf_download_name(report_id),
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "photo_count": photo_count,
        "pdf_size_bytes": len(pdf_bytes),
    }


def create_field_photo_report_pdf(
    fields: dict[str, str],
    photo_ids: list[Any],
    *,
    lat: Any,
    lon: Any,
    parcel: dict[str, Any] | None = None,
    parcel_error: Any = "",
    field_photos_dir: Path,
) -> dict[str, Any]:
    crop_m = _report_crop_m(fields)
    fields = report_models.validate_report_fields(fields)
    report_id = _report_id("field_photo_group", fields)
    photo_records = _field_photo_records(photo_ids, field_photos_dir)

    with TemporaryDirectory(prefix=f"{report_id}_") as work_dir_name:
        work_dir = Path(work_dir_name)
        report_record = _field_photo_report_record(
            photo_records=photo_records,
            lat=lat,
            lon=lon,
            parcel=parcel,
            parcel_error=parcel_error,
            report_root=work_dir,
        )
        evidence = _build_report_evidence(report_record, work_dir, crop_m=crop_m)
        report_record = _record_with_report_evidence(report_record, evidence)
        subject, mail_body = report_mail.build_mail_draft(report_record, evidence, fields)
        pdf_bytes = report_pdf.build_report_pdf(
            record=report_record,
            evidence=evidence,
            record_dir=work_dir,
            evidence_base_dir=work_dir,
            recipient=config.REPORT_RECIPIENT,
            subject=subject,
            mail_body=mail_body,
        )

    return _download_payload(
        report_id=report_id,
        recipient=config.REPORT_RECIPIENT,
        subject=subject,
        photo_count=_approved_photo_count(report_record),
        pdf_bytes=pdf_bytes,
    )

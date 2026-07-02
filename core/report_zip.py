from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from core import report_html, report_models
from core.photo_privacy import is_approved


def _safe_child(base_dir: Path, relative_path: str) -> Path:
    root = base_dir.resolve()
    path = (base_dir / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError("Nieprawidłowa ścieżka w sprawie pojazdu.")
    return path


def _archive_attached_photos(archive: zipfile.ZipFile, record_dir: Path, record: dict[str, Any]) -> None:
    photos = record.get("attached_photos") if isinstance(record.get("attached_photos"), list) else []
    for photo in photos:
        if not isinstance(photo, dict) or not is_approved(photo):
            continue
        for key in ("public_thumb_file", "public_image_file"):
            rel = str(photo.get(key) or "")
            if not rel:
                continue
            path = _safe_child(record_dir, rel)
            if path.exists():
                archive.write(path, rel)


def _archive_public_evidence_photos(
    archive: zipfile.ZipFile,
    record_dir: Path,
    evidence: dict[str, Any],
    *,
    archive_root: str = "miniatury_historyczne",
) -> None:
    evidence_dir = _safe_child(record_dir, str(evidence.get("path") or ""))
    for crop in evidence.get("crops") or []:
        if not isinstance(crop, dict):
            continue
        label = report_models.safe_filename(str(crop.get("label") or "miniatura"), "miniatura", ".jpg")
        crop_path = evidence_dir / str(crop.get("file") or "")
        if crop_path.exists():
            archive.write(crop_path, f"{archive_root}/{label}")


def write_public_zip(
    zip_path: Path,
    record_dir: Path,
    record: dict[str, Any],
    evidence: dict[str, Any],
    recipient: str,
    subject: str,
    mail_body: str,
    photos: list[report_models.PreparedReportPhoto],
) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("zgloszenie.txt", f"Do: {recipient}\nTemat: {subject}\n\n{mail_body}")
        archive.writestr(
            "raport.html", report_html.build_public_report_html(record, evidence, subject, mail_body, photos)
        )
        _archive_attached_photos(archive, record_dir, record)
        _archive_public_evidence_photos(archive, record_dir, evidence)
        for photo in photos:
            archive.writestr(f"zdjecia_z_miejsca/{photo.optimized_name}", photo.optimized_data)


def write_admin_zip(
    zip_path: Path,
    record_dir: Path,
    record: dict[str, Any],
    evidence: dict[str, Any],
    recipient: str,
    subject: str,
    mail_body: str,
    photos: list[report_models.PreparedReportPhoto],
) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("zgloszenie.txt", f"Do: {recipient}\nTemat: {subject}\n\n{mail_body}")
        archive.writestr(
            "raport.html",
            report_html.build_admin_report_html(record_dir, record, recipient, subject, mail_body, photos),
        )

        _archive_attached_photos(archive, record_dir, record)
        _archive_public_evidence_photos(archive, record_dir, evidence)

        for photo in photos:
            archive.writestr(f"zdjecia_z_miejsca/{photo.optimized_name}", photo.optimized_data)

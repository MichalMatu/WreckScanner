from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from core import config
from core.field_photos import FIELD_PHOTO_ID_RE
from core.photo_privacy import REVIEW_STATUSES, normalize_redactions


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    path: Path,
    message: str,
    **extra: Any,
) -> None:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "path": path.as_posix(),
        "message": message,
    }
    item.update({key: value for key, value in extra.items() if value is not None})
    issues.append(item)


def _is_safe_relative_path(value: Any) -> bool:
    text = str(value or "").replace("\\", "/").strip()
    if not text or text.startswith("/"):
        return False
    return all(part not in {"", ".", ".."} for part in text.split("/"))


def _safe_child(root: Path, relative_path: Any) -> Path | None:
    if not _is_safe_relative_path(relative_path):
        return None
    root_resolved = root.resolve()
    child = (root / str(relative_path)).resolve()
    if root_resolved == child or root_resolved in child.parents:
        return child
    return None


def _is_coord(value: Any, min_value: float, max_value: float) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and min_value <= number <= max_value


def _image_info(path: Path, issues: list[dict[str, Any]], *, severity: str = "error") -> dict[str, Any] | None:
    try:
        with Image.open(path) as image:
            return {
                "format": str(image.format or ""),
                "width": int(image.size[0]),
                "height": int(image.size[1]),
            }
    except (OSError, UnidentifiedImageError) as exc:
        _issue(issues, severity, "image_unreadable", path, f"Nie da się odczytać obrazu: {exc}")
        return None


def _count_bytes(path: Path | None) -> int:
    try:
        return path.stat().st_size if path and path.is_file() else 0
    except OSError:
        return 0


def _audit_private_photo_file(
    private_photos_dir: Path,
    record_path: Path,
    record: dict[str, Any],
    issues: list[dict[str, Any]],
    code_prefix: str,
    *,
    check_images: bool,
) -> tuple[Path | None, int]:
    value = record.get("private_original_file")
    if not value:
        if record.get("private_original_deleted_at"):
            return None, 0
        _issue(
            issues, "error", f"{code_prefix}_missing_private_original", record_path, "Brak pola private_original_file."
        )
        return None, 0
    file_path = _safe_child(private_photos_dir, value)
    if not file_path:
        _issue(
            issues,
            "error",
            f"{code_prefix}_unsafe_private_original_path",
            record_path,
            "Niebezpieczna ścieżka prywatnego oryginału.",
        )
        return None, 0
    if not file_path.exists():
        _issue(
            issues,
            "error",
            f"{code_prefix}_private_original_missing",
            file_path,
            "Brakuje prywatnego oryginału zdjęcia.",
        )
        return file_path, 0

    byte_count = _count_bytes(file_path)
    if check_images:
        info = _image_info(file_path, issues)
        width = record.get("image_width")
        height = record.get("image_height")
        if (
            info
            and isinstance(width, int)
            and isinstance(height, int)
            and (info["width"], info["height"]) != (width, height)
        ):
            _issue(
                issues,
                "warning",
                f"{code_prefix}_size_mismatch",
                file_path,
                "Rozmiar prywatnego oryginału nie zgadza się z record.json.",
                image_width=info["width"],
                image_height=info["height"],
                record_width=width,
                record_height=height,
            )
    return file_path, byte_count


def _audit_public_photo_file(
    record_dir: Path,
    record_path: Path,
    record: dict[str, Any],
    key: str,
    issues: list[dict[str, Any]],
    code_prefix: str,
    *,
    check_images: bool,
    expected_thumbnail: bool = False,
    thumb_max_edge: int = config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
) -> tuple[Path | None, int]:
    value = record.get(key)
    if not value:
        _issue(issues, "error", f"{code_prefix}_missing", record_path, f"Brak pola {key}.")
        return None, 0
    file_path = _safe_child(record_dir, value)
    if not file_path:
        _issue(
            issues,
            "error",
            f"{code_prefix}_unsafe_path",
            record_path,
            f"Niebezpieczna ścieżka {key}.",
        )
        return None, 0
    if not file_path.exists():
        _issue(issues, "error", f"{code_prefix}_missing_file", file_path, f"Brakuje pliku wskazanego przez {key}.")
        return file_path, 0

    byte_count = _count_bytes(file_path)
    if check_images:
        info = _image_info(file_path, issues)
        if info and expected_thumbnail:
            max_edge = max(info["width"], info["height"])
            if max_edge > thumb_max_edge:
                _issue(
                    issues,
                    "warning",
                    f"{code_prefix}_too_large",
                    file_path,
                    f"Miniatura ma {max_edge}px na dłuższej krawędzi.",
                    max_edge_px=max_edge,
                )
    return file_path, byte_count


def _audit_review_fields(
    record_path: Path,
    record: dict[str, Any],
    issues: list[dict[str, Any]],
    code_prefix: str,
) -> str:
    status = str(record.get("public_review_status") or "").strip()
    if status not in REVIEW_STATUSES:
        _issue(
            issues,
            "error",
            f"{code_prefix}_bad_review_status",
            record_path,
            "Brak albo nieprawidłowy public_review_status.",
            public_review_status=status,
        )
    try:
        normalized_redactions = normalize_redactions(record.get("redactions") or [])
    except ValueError:
        _issue(
            issues,
            "error",
            f"{code_prefix}_bad_redactions",
            record_path,
            "Pole redactions musi być listą poprawnych wielokątów.",
        )
    else:
        if normalized_redactions != record.get("redactions"):
            _issue(
                issues,
                "warning",
                f"{code_prefix}_retired_redactions",
                record_path,
                "Pole redactions używa wycofanego formatu.",
            )
    return status


def _audit_retired_photo_fields(
    record_path: Path,
    record: dict[str, Any],
    issues: list[dict[str, Any]],
    code_prefix: str,
) -> None:
    retired_keys = ("original_file", "thumbnail_file", "thumb_file", "original_url", "original_path")
    present = [key for key in retired_keys if key in record]
    if present:
        _issue(
            issues,
            "error",
            f"{code_prefix}_retired_public_original",
            record_path,
            "Rekord nadal zawiera wycofane publiczne pola zdjęcia.",
            retired_fields=present,
        )


def _audit_field_photos(
    field_photos_dir: Path,
    private_photos_dir: Path,
    issues: list[dict[str, Any]],
    *,
    check_images: bool,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "records": 0,
        "issue_types": dict.fromkeys(config.FIELD_PHOTO_ISSUE_TYPES, 0),
        "unknown_issue_types": 0,
        "private_original_bytes": 0,
        "public_image_bytes": 0,
        "public_thumb_bytes": 0,
        "orphan_directories": 0,
        "orphan_files": 0,
    }
    issue_counter = Counter()
    field_photo_ids: set[str] = set()

    if not field_photos_dir.exists():
        _issue(
            issues, "warning", "field_photos_dir_missing", field_photos_dir, "Katalog zdjęć terenowych nie istnieje."
        )
        summary["ids"] = []
        return summary

    for child in sorted(field_photos_dir.iterdir()):
        if child.is_file():
            summary["orphan_files"] += 1
            _issue(issues, "warning", "field_photo_orphan_file", child, "Plik leży bezpośrednio w katalogu zdjęć.")
            continue
        if not child.is_dir():
            continue

        record_path = child / "record.json"
        if not record_path.exists():
            summary["orphan_directories"] += 1
            _issue(issues, "error", "field_photo_record_missing", child, "Katalog zdjęcia nie ma record.json.")
            continue
        try:
            record = _read_json(record_path)
        except (OSError, json.JSONDecodeError) as exc:
            _issue(
                issues, "error", "field_photo_record_unreadable", record_path, f"Nie da się odczytać record.json: {exc}"
            )
            continue
        if not isinstance(record, dict):
            _issue(issues, "error", "field_photo_record_not_object", record_path, "record.json nie jest obiektem JSON.")
            continue

        summary["records"] += 1
        photo_id = str(record.get("id") or "")
        photo_id_valid = bool(FIELD_PHOTO_ID_RE.fullmatch(photo_id))
        if not photo_id_valid:
            _issue(
                issues, "error", "field_photo_bad_id", record_path, "Nieprawidłowy identyfikator zdjęcia.", id=photo_id
            )
        else:
            field_photo_ids.add(photo_id)
        if photo_id and photo_id != child.name:
            _issue(
                issues, "error", "field_photo_id_folder_mismatch", record_path, "ID nie zgadza się z nazwą katalogu."
            )

        if "issue_type" not in record:
            issue_type = ""
            _issue(issues, "error", "field_photo_missing_issue_type", record_path, "Brak typu pinezki.")
        else:
            issue_type = str(record.get("issue_type") or "").strip()
        if issue_type not in config.FIELD_PHOTO_ISSUE_TYPES:
            summary["unknown_issue_types"] += 1
            _issue(
                issues,
                "error",
                "field_photo_bad_issue_type",
                record_path,
                "Nieprawidłowy typ pinezki.",
                issue_type=issue_type,
            )
        else:
            issue_counter[issue_type] += 1

        if not _is_coord(record.get("lat"), -90, 90) or not _is_coord(record.get("lon"), -180, 180):
            _issue(issues, "error", "field_photo_bad_coordinates", record_path, "Nieprawidłowe współrzędne zdjęcia.")

        _audit_retired_photo_fields(record_path, record, issues, "field_photo")
        status = _audit_review_fields(record_path, record, issues, "field_photo")
        _, original_bytes = _audit_private_photo_file(
            private_photos_dir,
            record_path,
            record,
            issues,
            "field_photo",
            check_images=check_images,
        )
        summary["private_original_bytes"] += original_bytes

        if status == "approved":
            _, public_bytes = _audit_public_photo_file(
                child,
                record_path,
                record,
                "public_image_file",
                issues,
                "field_photo_public_image",
                check_images=check_images,
            )
            _, thumb_bytes = _audit_public_photo_file(
                child,
                record_path,
                record,
                "public_thumb_file",
                issues,
                "field_photo_public_thumb",
                check_images=check_images,
                expected_thumbnail=True,
                thumb_max_edge=config.FIELD_PHOTO_THUMBNAIL_MAX_EDGE_PX,
            )
            summary["public_image_bytes"] += public_bytes
            summary["public_thumb_bytes"] += thumb_bytes
        elif record.get("public_image_file") or record.get("public_thumb_file"):
            _issue(
                issues,
                "error",
                "field_photo_public_asset_without_approval",
                record_path,
                "Niezatwierdzony rekord wskazuje publiczne pliki zdjęcia.",
            )

    summary["issue_types"] = {key: int(issue_counter.get(key, 0)) for key in config.FIELD_PHOTO_ISSUE_TYPES}
    summary["ids"] = sorted(field_photo_ids)
    return summary


def run_data_diagnostics(
    *,
    field_photos_dir: Path = config.FIELD_PHOTOS_DIR,
    private_photos_dir: Path = config.PRIVATE_PHOTOS_DIR,
    check_images: bool = True,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    field_summary = _audit_field_photos(field_photos_dir, private_photos_dir, issues, check_images=check_images)
    field_summary.pop("ids", None)
    by_severity = Counter(issue["severity"] for issue in issues)
    status = "error" if by_severity.get("error", 0) else "warning" if by_severity.get("warning", 0) else "ok"
    return {
        "generated_at": _now_iso(),
        "status": status,
        "roots": {
            "field_photos_dir": field_photos_dir.as_posix(),
            "private_photos_dir": private_photos_dir.as_posix(),
        },
        "checks": {
            "images": check_images,
        },
        "summary": {
            "field_photos": field_summary,
            "issues": {
                "total": len(issues),
                "by_severity": {key: int(by_severity.get(key, 0)) for key in ("error", "warning", "info")},
            },
        },
        "issues": issues,
    }


def format_data_diagnostics(report: dict[str, Any]) -> str:
    field = report["summary"]["field_photos"]
    issue_summary = report["summary"]["issues"]
    issue_types = field["issue_types"]
    lines = [
        "Diagnostyka danych WreckScanner",
        f"Status: {str(report['status']).upper()}",
        f"Zdjęcia terenowe: {field['records']} rekordów",
        "  typy: "
        + ", ".join(
            f"{config.FIELD_PHOTO_ISSUE_TYPES[key]}={issue_types.get(key, 0)}" for key in config.FIELD_PHOTO_ISSUE_TYPES
        ),
        "  pliki: "
        f"prywatne oryginały {_human_bytes(field['private_original_bytes'])}, "
        f"publiczne kopie {_human_bytes(field['public_image_bytes'])}, "
        f"publiczne miniatury {_human_bytes(field['public_thumb_bytes'])}",
        "Problemy: "
        f"{issue_summary['by_severity']['error']} error, "
        f"{issue_summary['by_severity']['warning']} warning, "
        f"{issue_summary['by_severity']['info']} info",
    ]
    if report["issues"]:
        lines.append("")
        lines.append("Lista problemów:")
        for issue in report["issues"]:
            lines.append(f"- [{issue['severity'].upper()}] {issue['code']} {issue['path']} - {issue['message']}")
    return "\n".join(lines)


def _human_bytes(value: Any) -> str:
    size = float(value or 0)
    units = ("B", "KB", "MB", "GB")
    unit = units[0]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            break
        size /= 1024
    return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"

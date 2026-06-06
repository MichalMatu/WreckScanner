from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from core import config

REQUIRED_REPORT_FIELDS = {
    "reporter_name": "imię i nazwisko",
    "reporter_address": "adres zamieszkania",
    "reporter_phone": "telefon",
    "reporter_email": "adres e-mail",
    "location_description": "dokładne miejsce pojazdu",
    "observed_at": "data i godzina obserwacji",
    "vehicle_description": "opis stanu pojazdu",
}


@dataclass(frozen=True)
class ReportPhotoUpload:
    field_name: str
    filename: str
    content_type: str
    data: bytes


@dataclass(frozen=True)
class PreparedReportPhoto:
    original_name: str
    optimized_name: str
    original_data: bytes
    optimized_data: bytes
    content_type: str
    size_bytes: int
    optimized_size_bytes: int


@dataclass(frozen=True)
class ReportPackageAccess:
    token: str
    expires_at: str


def safe_text(value: Any, max_len: int = 4000) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) > max_len:
        raise ValueError("Jedno z pól formularza jest zbyt długie.")
    return text


def validate_report_fields(raw_fields: dict[str, str]) -> dict[str, str]:
    fields = {key: safe_text(raw_fields.get(key)) for key in REQUIRED_REPORT_FIELDS}
    missing = [label for key, label in REQUIRED_REPORT_FIELDS.items() if not fields[key]]
    if missing:
        raise ValueError("Uzupełnij wymagane pola: " + ", ".join(missing) + ".")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", fields["reporter_email"]):
        raise ValueError("Podaj prawidłowy adres e-mail zgłaszającego.")
    return fields


def safe_filename(raw_name: str, fallback: str, ext: str) -> str:
    stem = Path(raw_name or "").stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or fallback
    stem = stem[:70]
    return f"{stem}{ext}"


def deduped_filename(name: str, used_names: set[str], ext: str) -> str:
    if name not in used_names:
        return name
    stem = Path(name).stem
    duplicate_idx = 2
    while True:
        candidate = f"{stem}_{duplicate_idx}{ext}"
        if candidate not in used_names:
            return candidate
        duplicate_idx += 1


def image_to_optimized_jpeg(image: Image.Image) -> bytes:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    image.thumbnail(
        (config.OPTIMIZED_PHOTO_MAX_EDGE_PX, config.OPTIMIZED_PHOTO_MAX_EDGE_PX),
        Image.Resampling.LANCZOS,
    )
    out = io.BytesIO()
    image.save(out, "JPEG", quality=config.OPTIMIZED_PHOTO_JPEG_QUALITY, optimize=True)
    return out.getvalue()


def prepare_report_photos(uploads: list[ReportPhotoUpload]) -> list[PreparedReportPhoto]:
    uploads = [upload for upload in uploads if upload.filename or upload.data]
    if len(uploads) > config.MAX_REPORT_PHOTOS:
        raise ValueError(f"Możesz dodać maksymalnie {config.MAX_REPORT_PHOTOS} zdjęć.")

    prepared: list[PreparedReportPhoto] = []
    used_original_names: set[str] = set()
    for idx, upload in enumerate(uploads, start=1):
        size = len(upload.data)
        if size > config.MAX_REPORT_PHOTO_BYTES:
            raise ValueError(f"Zdjęcie {upload.filename or idx} przekracza limit 10 MB.")
        if size <= 0:
            continue
        try:
            with Image.open(io.BytesIO(upload.data)) as img:
                image_format = str(img.format or "").upper()
                if image_format not in config.ALLOWED_REPORT_PHOTO_EXTENSIONS:
                    raise ValueError("Dozwolone są tylko zdjęcia JPG, PNG albo WebP.")
                optimized = image_to_optimized_jpeg(img)
        except UnidentifiedImageError as exc:
            raise ValueError(f"Plik {upload.filename or idx} nie jest obsługiwanym zdjęciem.") from exc

        ext = config.ALLOWED_REPORT_PHOTO_EXTENSIONS[image_format]
        base_original_name = safe_filename(upload.filename, f"zdjecie_{idx:02d}", ext)
        original_name = deduped_filename(base_original_name, used_original_names, ext)
        used_original_names.add(original_name)
        optimized_name = f"zdjecie_{idx:02d}.jpg"
        prepared.append(
            PreparedReportPhoto(
                original_name=original_name,
                optimized_name=optimized_name,
                original_data=upload.data,
                optimized_data=optimized,
                content_type=upload.content_type,
                size_bytes=size,
                optimized_size_bytes=len(optimized),
            )
        )
    return prepared

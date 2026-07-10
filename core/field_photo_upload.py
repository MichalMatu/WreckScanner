from __future__ import annotations

import io
import os
import warnings
from contextlib import suppress
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any

from PIL import Image, UnidentifiedImageError

from core import config
from core.uploads import UploadedFile

_DECODE_SEMAPHORE = BoundedSemaphore(config.FIELD_PHOTO_MAX_CONCURRENT_DECODES)


def _safe_text(value: Any, max_len: int = 300) -> str:
    return str(value or "").replace("\x00", "").strip()[:max_len]


def _format_exif_datetime(value: Any) -> str | None:
    text = _safe_text(value, 80)
    parts = text.replace(" ", ":").replace("T", ":").split(":")
    if len(parts) != 6 or not all(part.isdigit() for part in parts):
        return text or None
    year, month, day, hour, minute, second = parts
    if not all(len(part) == length for part, length in zip(parts, (4, 2, 2, 2, 2, 2), strict=True)):
        return text or None
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}"


def _limited_exif(exif: Image.Exif) -> dict[str, str]:
    labels = {
        271: "make",
        272: "model",
        306: "datetime",
        36867: "datetime_original",
        36868: "datetime_digitized",
    }
    values: dict[str, str] = {}
    for tag, label in labels.items():
        value = _safe_text(exif.get(tag), 200)
        if value:
            values[label] = value
    return values


def validated_upload_image(upload: UploadedFile) -> tuple[str, int, int, str | None, dict[str, str]]:
    try:
        with _DECODE_SEMAPHORE, warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(upload.data)) as image:
                image_format = str(image.format or "").upper()
                if image_format not in config.ALLOWED_UPLOAD_IMAGE_FORMATS:
                    raise ValueError("Dozwolone są tylko zdjęcia JPG, PNG albo WebP.")
                width, height = image.size
                if width <= 0 or height <= 0:
                    raise ValueError("Zdjęcie ma nieprawidłowe wymiary.")
                if (
                    width > config.MAX_FIELD_PHOTO_EDGE_PX
                    or height > config.MAX_FIELD_PHOTO_EDGE_PX
                    or width * height > config.MAX_FIELD_PHOTO_PIXELS
                ):
                    raise ValueError(
                        "Zdjęcie ma zbyt dużą rozdzielczość. "
                        f"Limit to {config.MAX_FIELD_PHOTO_PIXELS // 1_000_000} MP i "
                        f"{config.MAX_FIELD_PHOTO_EDGE_PX} px na krawędź."
                    )
                image.verify()
            with Image.open(io.BytesIO(upload.data)) as decoded:
                if str(decoded.format or "").upper() != image_format or decoded.size != (width, height):
                    raise ValueError("Plik zdjęcia ma niespójne metadane.")
                decoded.load()
                exif = decoded.getexif()
                captured_at = _format_exif_datetime(exif.get(36867) or exif.get(306))
                limited_exif = _limited_exif(exif)
    except ValueError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        UnidentifiedImageError,
    ) as exc:
        raise ValueError("Plik jest uszkodzonym albo zbyt dużym zdjęciem.") from exc
    return image_format, width, height, captured_at, limited_exif


def write_bytes_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.{os.urandom(6).hex()}.tmp")
    try:
        temp_path.write_bytes(data)
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
    finally:
        with suppress(OSError):
            temp_path.unlink()

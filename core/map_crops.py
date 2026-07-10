from __future__ import annotations

import math
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageStat

from core import config
from core.geo import bbox_3857, bbox_4326
from core.http_response import read_limited_response_bytes, response_content_type


@dataclass(frozen=True)
class LocationCrop:
    label: str
    image: Image.Image


def validate_crop_m(value: Any) -> float:
    try:
        crop_m = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Nieprawidlowy zoom wycinka mapy.") from exc
    if not math.isfinite(crop_m) or not config.REVIEW_CROP_M_MIN <= crop_m <= config.REVIEW_CROP_M_MAX:
        raise ValueError(
            f"Zoom wycinka mapy musi byc w zakresie {config.REVIEW_CROP_M_MIN:g}-{config.REVIEW_CROP_M_MAX:g} m."
        )
    return crop_m


def _safe_crop_label(value: Any) -> str:
    label = str(value or "").strip()
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("._-")
    return label[:80] or "crop"


def _crop_px(crop_m: float) -> int:
    pixels = int(round(crop_m * config.ORTHO_CROP_PIXELS_PER_METER))
    return max(config.ORTHO_CROP_MIN_PX, min(config.ORTHO_CROP_MAX_PX, pixels))


def _bbox_4326_dict(bbox: str) -> dict[str, float]:
    min_lat, min_lon, max_lat, max_lon = [float(part) for part in bbox.split(",")]
    return {
        "min_lat": min_lat,
        "min_lon": min_lon,
        "max_lat": max_lat,
        "max_lon": max_lon,
    }


def _bbox_3857_dict(bbox: str) -> dict[str, float]:
    min_x, min_y, max_x, max_y = [float(part) for part in bbox.split(",")]
    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
    }


def _wms_url(year: int) -> str:
    return f"{config.ORTHO_WMS_BASE}/OGC_ortofoto_{int(year)}/MapServer/WMSServer"


def _looks_blank(image: Image.Image) -> bool:
    rgba = image.convert("RGBA")
    alpha_extrema = rgba.getchannel("A").getextrema()
    if alpha_extrema[1] == 0:
        return True

    rgb = rgba.convert("RGB")
    extrema = rgb.getextrema()
    channel_span = max((high - low for low, high in extrema), default=0)
    if channel_span > config.ORTHO_BLANK_IMAGE_STD_THRESHOLD:
        return False

    stat = ImageStat.Stat(rgb.convert("L"))
    return bool(stat.stddev and stat.stddev[0] <= config.ORTHO_BLANK_IMAGE_STD_THRESHOLD)


def _download_crop_image_once(
    *,
    session: requests.Session,
    year: int,
    bbox: str,
    size_px: int,
) -> Image.Image | None:
    try:
        response = session.get(
            _wms_url(year),
            params={
                "SERVICE": "WMS",
                "VERSION": "1.3.0",
                "REQUEST": "GetMap",
                "LAYERS": "1",
                "STYLES": "",
                "CRS": "EPSG:3857",
                "BBOX": bbox,
                "WIDTH": str(size_px),
                "HEIGHT": str(size_px),
                "FORMAT": "image/png",
            },
            timeout=config.ORTHO_WMS_TIMEOUT,
            stream=True,
        )
        if response.status_code != 200:
            return None
        if response_content_type(response) not in {"image/png", "application/octet-stream"}:
            return None
        response_content = read_limited_response_bytes(response, max_bytes=config.MAX_ORTHO_RESPONSE_BYTES)
    except (requests.RequestException, ValueError):
        return None
    finally:
        if "response" in locals() and callable(getattr(response, "close", None)):
            response.close()
    if b"Exception" in response_content[:2048]:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(response_content)) as raw_image:
                width, height = raw_image.size
                if (
                    width <= 0
                    or height <= 0
                    or width > config.ORTHO_CROP_MAX_PX
                    or height > config.ORTHO_CROP_MAX_PX
                    or width * height > config.ORTHO_CROP_MAX_PX**2
                ):
                    return None
                raw_image.load()
                image = raw_image.convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError):
        return None

    if _looks_blank(image):
        return None
    return image


def _download_crop_image(
    *,
    session: requests.Session,
    year: int,
    bbox: str,
    size_px: int,
) -> Image.Image | None:
    attempts = max(1, int(config.ORTHO_CROP_RETRY_ATTEMPTS))
    for attempt in range(attempts):
        image = _download_crop_image_once(session=session, year=year, bbox=bbox, size_px=size_px)
        if image is not None:
            return image
        if attempt < attempts - 1:
            time.sleep(config.ORTHO_CROP_RETRY_DELAY_SECONDS * (attempt + 1))
    return None


def fetch_location_crops(
    lat: float,
    lon: float,
    *,
    crop_m: Any = config.REVIEW_CROP_M,
    years: list[int] | tuple[int, ...] = tuple(config.ORTHO_YEARS),
    session: requests.Session | None = None,
) -> tuple[list[LocationCrop], dict[str, Any]]:
    crop_m_f = validate_crop_m(crop_m)
    size_px = _crop_px(crop_m_f)
    bbox = bbox_3857(lat, lon, crop_m_f, crop_m_f)
    readable_bbox = bbox_4326(lat, lon, crop_m_f, crop_m_f)
    years_to_fetch = [int(year) for year in years]

    crops: list[LocationCrop] = []

    def download_year(year: int) -> tuple[int, Image.Image | None]:
        if session is not None:
            return year, _download_crop_image(session=session, year=year, bbox=bbox, size_px=size_px)
        http = requests.Session()
        try:
            return year, _download_crop_image(session=http, year=year, bbox=bbox, size_px=size_px)
        finally:
            http.close()

    max_workers = max(1, min(len(years_to_fetch), config.ORTHO_CROP_MAX_WORKERS))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = [executor.submit(download_year, year) for year in years_to_fetch]

    for result in results:
        year, image = result.result()
        if image is not None:
            crops.append(LocationCrop(label=_safe_crop_label(year), image=image))

    if not crops:
        raise FileNotFoundError("Nie udało się pobrać ortofotomap dla tego miejsca.")

    fetched_years = [int(crop.label) for crop in crops if crop.label.isdigit()]
    fetched_year_set = set(fetched_years)
    metadata = {
        "center_lat": lat,
        "center_lon": lon,
        "crop_meters": crop_m_f,
        "image_size_px": size_px,
        "bbox_4326": _bbox_4326_dict(readable_bbox),
        "bbox_3857": _bbox_3857_dict(bbox),
        "requested_years": years_to_fetch,
        "years": fetched_years,
        "missing_years": [year for year in years_to_fetch if year not in fetched_year_set],
        "source": "wroclaw_wms_location_crops",
    }
    return crops, metadata


def save_location_crops(
    lat: float,
    lon: float,
    output_dir: Path,
    *,
    crop_m: Any = config.REVIEW_CROP_M,
    years: list[int] | tuple[int, ...] = tuple(config.ORTHO_YEARS),
    filename_prefix: str = "",
    jpeg_quality: int = config.REVIEW_JPEG_QUALITY,
    session: requests.Session | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    crops, metadata = fetch_location_crops(lat, lon, crop_m=crop_m, years=years, session=session)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: list[dict[str, str]] = []
    for crop in crops:
        file_name = f"{filename_prefix}{crop.label}.jpg"
        crop.image.save(output_dir / file_name, "JPEG", quality=jpeg_quality)
        saved.append({"label": crop.label, "file": file_name})
    return saved, metadata


def crop_to_data_url(crop: LocationCrop, *, jpeg_quality: int = config.REVIEW_JPEG_QUALITY) -> str:
    buffer = BytesIO()
    crop.image.save(buffer, "JPEG", quality=jpeg_quality)
    import base64

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"

import json
import logging
import math
import subprocess  # nosec B404
import sys
import threading
import time
from pathlib import Path

from app import config, map_downloads, pipeline
from app.http import access
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from core import config as core_config
from core.map_crops import save_scan_crops, validate_crop_m
from core.runtime import subprocess_text_kwargs

logger = logging.getLogger("wreckscanner.server")

_download_progress_lock = threading.Lock()
_download_progress = {
    "status": "idle",
    "stage": None,
    "message": "",
    "percent": None,
    "updated_at": None,
}
_WFS_DOWNLOADED_CACHE_STATES = {"downloaded", "resumed", "restarted"}


def set_download_progress(**payload) -> None:
    with _download_progress_lock:
        _download_progress.clear()
        _download_progress.update(
            {
                "status": "active",
                "stage": None,
                "message": "",
                "percent": None,
                "updated_at": time.time(),
            }
        )
        _download_progress.update(payload)


def get_download_progress() -> dict:
    with _download_progress_lock:
        return dict(_download_progress)


def versioned_route_url(route_path: str, version: str) -> str:
    separator = "&" if "?" in route_path else "?"
    return f"{route_path}{separator}v={version}"


def file_asset_version(path: Path) -> str:
    try:
        return str(path.stat().st_mtime_ns)
    except OSError:
        return str(time.time_ns())


def handle_download_progress(handler) -> None:
    http_responses.send_json(handler, 200, get_download_progress())


def require_download_capacity() -> None:
    pressure = pipeline.system_pressure()
    if pressure["overloaded"]:
        raise pipeline.HttpJsonError(
            503,
            "Raspberry Pi jest teraz przeciazone: " + "; ".join(pressure["reasons"]),
        )


def download_area_params(data: dict) -> tuple[float, float, float]:
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
        width = float(data.get("width", 50))
        height = float(data.get("height", 50))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Nieprawidlowe parametry skanowania.") from exc
    area_m = max(width, height)
    if not math.isfinite(area_m) or area_m < config.MIN_SCAN_SIZE_M or area_m > config.MAX_SCAN_SIZE_M:
        raise ValueError(f"Obszar analizy musi miec maksymalnie {config.MAX_SCAN_SIZE_M:g} m.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Nieprawidlowe wspolrzedne.")
    return lat, lon, area_m


def log_download_request(handler, lat: float, lon: float, area_m: float) -> None:
    logger.info(
        "Download request request_id=%s lat=%s lon=%s area_m=%s density_px=%s",
        http_responses.request_id(handler),
        lat,
        lon,
        area_m,
        core_config.NATIVE_TILE_PX,
    )


def update_download_progress(**payload) -> None:
    current = payload.pop("current", None)
    total = payload.pop("total", None)
    percent = pipeline.progress_percent(current, total) if current is not None and total is not None else None
    set_download_progress(
        status="active",
        percent=percent,
        current=current,
        total=total,
        **payload,
    )


def download_progress_callback():
    def progress(**payload):
        update_download_progress(**payload)

    return progress


def download_wfs_metrics(wfs_summary: list[dict]) -> dict:
    wfs_replaced = [item for item in wfs_summary if item.get("status") == "replaced"]
    return {
        "wfs_replaced": len(wfs_replaced),
        "wfs_cache_hits": sum(1 for item in wfs_replaced if item.get("cache") == "hit"),
        "wfs_downloaded": sum(1 for item in wfs_replaced if item.get("cache") in _WFS_DOWNLOADED_CACHE_STATES),
        "wfs_skipped": sum(1 for item in wfs_summary if item.get("status") != "replaced"),
    }


def download_response_payload(results: dict, bbox, wfs_summary: list[dict], pipeline_token: str) -> dict:
    return {
        "status": "completed",
        "saved": sum(1 for item in results.values() if item.get("status") == "ok"),
        "missing": sum(1 for item in results.values() if item.get("status") == "missing"),
        "total": len(config.WMS_YEARS),
        **download_wfs_metrics(wfs_summary),
        "job_token": pipeline_token,
        "bbox": bbox,
    }


def handle_download(handler) -> None:
    if not access.require_public_feature(
        handler, "scan_analysis", "Skanowanie i analiza YOLO sa teraz wylaczone dla niezalogowanych."
    ):
        return
    pipeline_token = None
    try:
        require_download_capacity()
        lat, lon, area_m = download_area_params(http_request_body.read_json_body(handler))
        pipeline_token = pipeline.start_pipeline(pipeline.client_id(handler))
        log_download_request(handler, lat, lon, area_m)

        set_download_progress(status="active", stage="start", message="Przygotowuję pobieranie ortofotomap", percent=0)
        results, bbox, wfs_summary = map_downloads.download_maps(
            lat,
            lon,
            area_m,
            area_m,
            progress=download_progress_callback(),
        )
        set_download_progress(
            status="done",
            stage="done",
            message="Pobieranie zakończone",
            percent=100,
        )
        http_responses.send_json(handler, 200, download_response_payload(results, bbox, wfs_summary, pipeline_token))

    except pipeline.HttpJsonError as e:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        set_download_progress(status="error", stage="error", message=e.message, percent=None)
        http_responses.send_json(handler, e.status, {"error": e.message})
    except ValueError as e:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        set_download_progress(status="error", stage="error", message=str(e), percent=None)
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        public_error = "Nie udało się pobrać ortofotomap."
        set_download_progress(status="error", stage="error", message=public_error, percent=None)
        http_responses.send_internal_error(
            handler,
            500,
            "Map download pipeline failed",
            exc,
            public_error=public_error,
        )


def handle_inspect(handler) -> None:
    if not access.require_public_feature(
        handler, "manual_wrecks", "Dodawanie recznych pinezek jest teraz wylaczone dla niezalogowanych."
    ):
        return
    try:
        data = http_request_body.read_json_body(handler)
        try:
            lat = float(data["lat"])
            lon = float(data["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Nieprawidlowe wspolrzedne wycinka mapy.") from exc
        crop_m = validate_crop_m(data.get("cropM", core_config.REVIEW_CROP_M))

        custom_dir = config.ANALYSIS_DIR / "custom_crops"
        ts = int(time.time() * 1000)
        crops, _metadata = save_scan_crops(
            lat,
            lon,
            config.DOWNLOAD_DATA_DIR,
            custom_dir,
            crop_m=crop_m,
            filename_prefix=f"custom_{ts}_",
            jpeg_quality=config.INSPECT_JPEG_QUALITY,
        )
        http_responses.send_json(
            handler,
            200,
            {
                "status": "ok",
                "crops": [
                    {
                        "year": crop["label"],
                        "url": f"/{config.ANALYSIS_DIR_NAME}/custom_crops/{crop['file']}",
                    }
                    for crop in crops
                ],
            },
        )

    except (FileNotFoundError, ValueError) as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Manual map crop creation failed",
            exc,
            public_error="Nie udało się przygotować wycinków mapy.",
        )


def handle_analyze(handler) -> None:
    if not access.require_public_feature(
        handler, "scan_analysis", "Skanowanie i analiza YOLO sa teraz wylaczone dla niezalogowanych."
    ):
        return
    pipeline_token = None
    try:
        pressure = pipeline.system_pressure()
        if pressure["overloaded"]:
            raise pipeline.HttpJsonError(503, "Raspberry Pi jest teraz przeciazone: " + "; ".join(pressure["reasons"]))
        data = http_request_body.read_json_body(handler)
        pipeline_token = str(data.get("job_token", "")).strip()
        if not pipeline_token:
            raise pipeline.HttpJsonError(409, "Brak tokenu zadania. Uruchom skan od poczatku.")
        pipeline.advance_pipeline(pipeline_token, pipeline.client_id(handler), "analyze")

        cmd = [sys.executable, str(config.ANALYZE_SCRIPT)]
        model = str(data.get("model", "")).strip()
        if model:
            cmd.extend(["--model", model])
        device = str(data.get("device", "")).strip()
        if device:
            if device not in {"auto", "cpu", "mps"}:
                raise ValueError("Nieprawidłowe device. Dozwolone: auto, cpu, mps.")
            cmd.extend(["--device", device])
        lang = str(data.get("lang", "")).strip()
        if lang in {"pl", "en"}:
            cmd.extend(["--lang", lang])
        try:
            conf = float(data.get("conf", 0))
            if 0.05 <= conf <= 0.50:
                cmd.extend(["--conf", str(conf)])
        except (TypeError, ValueError):
            pass
        if data.get("fast") is True:
            cmd.append("--fast")
        crop_m = validate_crop_m(data.get("cropM", core_config.REVIEW_CROP_M))
        cmd.extend(["--crop-m", f"{crop_m:g}"])

        logger.info(
            "Starting analysis request_id=%s model=%s device=%s fast=%s",
            http_responses.request_id(handler),
            model or "default",
            device or "auto",
            data.get("fast") is True,
        )
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            **subprocess_text_kwargs(),
            timeout=config.ANALYZE_TIMEOUT_SECONDS,
        )  # nosec B603
        stdout = proc.stdout[-config.ANALYZE_STDOUT_TAIL_CHARS :]
        stderr = proc.stderr[-config.ANALYZE_STDERR_TAIL_CHARS :]
        candidates = []
        cand_path = config.ANALYSIS_DIR / "candidates.json"
        if cand_path.exists():
            with cand_path.open(encoding="utf-8") as f:
                candidates = json.load(f)
        report_version = file_asset_version(config.ROOT_DIR / config.ANALYSIS_DIR / "report.html")

        http_responses.send_json(
            handler,
            200,
            {
                "status": "ok" if proc.returncode == 0 else "error",
                "report_url": versioned_route_url(f"/{config.ANALYSIS_DIR_NAME}/report.html", report_version),
                "diagnostics_url": versioned_route_url(f"/{config.ANALYSIS_DIR_NAME}/run_log.json", report_version),
                "candidates": candidates[: config.ANALYZE_MAX_CANDIDATES],
                "stdout": stdout,
                "stderr": stderr,
            },
        )
        pipeline.finish_pipeline(pipeline_token)
    except subprocess.TimeoutExpired:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        http_responses.send_json(handler, 504, {"error": "Analiza trwała zbyt długo (>20 min)."})
    except pipeline.HttpJsonError as e:
        http_responses.send_json(handler, e.status, {"error": e.message})
    except ValueError as e:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        if pipeline_token:
            pipeline.finish_pipeline(pipeline_token)
        http_responses.send_internal_error(
            handler,
            500,
            "Analysis pipeline failed",
            exc,
            public_error="Nie udało się zakończyć analizy.",
        )

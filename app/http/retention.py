import logging
import threading
import time
from datetime import datetime, timezone

from app import config
from app.http import admin_session as http_admin_session
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from core import config as core_config
from core.photo_retention import retire_private_originals
from core.privacy_requests import purge_handled_privacy_request_content

logger = logging.getLogger("wreckscanner.server")

_photo_retention_run_lock = threading.Lock()
_photo_retention_state_lock = threading.Lock()
_photo_retention_scheduler_started = False
_photo_retention_state = {
    "running": False,
    "last_started_at": None,
    "last_finished_at": None,
    "last_source": None,
    "last_report": None,
    "last_error": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def snapshot() -> dict:
    with _photo_retention_state_lock:
        return dict(_photo_retention_state)


def run(*, dry_run: bool, source: str) -> dict:
    if not _photo_retention_run_lock.acquire(blocking=False):
        raise RuntimeError("Retencja zdjęć już działa.")
    try:
        with _photo_retention_state_lock:
            _photo_retention_state.update(
                {
                    "running": True,
                    "last_started_at": _now_iso(),
                    "last_source": source,
                    "last_error": None,
                }
            )
        report = retire_private_originals(
            field_photos_dir=core_config.FIELD_PHOTOS_DIR,
            private_photos_dir=core_config.PRIVATE_PHOTOS_DIR,
            dry_run=dry_run,
        )
        report["privacy_requests"] = purge_handled_privacy_request_content(dry_run=dry_run)
        with _photo_retention_state_lock:
            _photo_retention_state.update(
                {
                    "running": False,
                    "last_finished_at": _now_iso(),
                    "last_report": report,
                }
            )
        return report
    except Exception as exc:
        with _photo_retention_state_lock:
            _photo_retention_state.update(
                {
                    "running": False,
                    "last_finished_at": _now_iso(),
                    "last_error": str(exc),
                }
            )
        raise
    finally:
        _photo_retention_run_lock.release()


def start_scheduler(
    *,
    initial_delay_seconds: float = config.PHOTO_RETENTION_STARTUP_DELAY_SECONDS,
    interval_seconds: float = config.PHOTO_RETENTION_INTERVAL_SECONDS,
) -> bool:
    global _photo_retention_scheduler_started
    if not config.PHOTO_RETENTION_AUTORUN_ENABLED or _photo_retention_scheduler_started:
        return False
    _photo_retention_scheduler_started = True

    def worker() -> None:
        time.sleep(max(0.0, initial_delay_seconds))
        while True:
            try:
                run(dry_run=False, source="scheduler")
            except Exception as exc:
                logger.exception("Photo retention scheduler failed: %s", exc)
            time.sleep(max(1.0, interval_seconds))

    thread = threading.Thread(target=worker, name="photo-retention", daemon=True)
    thread.start()
    return True


def handle_run_photo_retention(handler) -> None:
    if not http_admin_session.require_admin(handler):
        return
    try:
        data = http_request_body.read_json_body(handler)
        dry_run = bool(data.get("dry_run", True))
        report = run(dry_run=dry_run, source="admin")
        http_responses.send_json(handler, 200, {"status": "ok", "report": report, "retention": snapshot()})
    except RuntimeError as e:
        http_responses.send_json(handler, 409, {"error": str(e)})
    except Exception as exc:
        public_error = "Nie udało się uruchomić retencji zdjęć."
        retention = snapshot()
        if retention.get("last_error"):
            retention["last_error"] = public_error
        http_responses.send_internal_error(
            handler,
            500,
            "Manual photo retention run failed",
            exc,
            public_error=public_error,
            payload={"retention": retention},
        )

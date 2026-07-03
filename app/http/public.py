import json

from app.http import access
from app.http import admin_session as http_admin_session
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from app.http import static_files as http_static_files
from app.http.public_data import lookup_cadastral_parcel
from core import config as core_config
from core.field_photos import (
    discard_field_photo_drafts_by_owner,
    field_photo_owner_original_asset,
    list_owner_field_photo_review_items,
    review_field_photo_by_owner,
    save_field_photo,
    submit_field_photos_by_owner,
)
from core.privacy_requests import create_privacy_request
from core.report_packages import create_field_photo_report_package
from core.uploads import UploadedFile


def reject_report_package_files(files: list[UploadedFile]) -> None:
    if any(file.filename or file.data for file in files):
        raise ValueError(
            "Raport można wygenerować tylko z zatwierdzonych zdjęć terenowych. "
            "Dodaj i zanonimizuj zdjęcia na mapie przed wygenerowaniem raportu."
        )


def _report_photo_ids(fields: dict[str, str]) -> list[str]:
    raw = fields.get("photo_ids") or ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in raw.split(",") if item.strip()]
    if not isinstance(parsed, list):
        raise ValueError("Nieprawidłowa lista zdjęć terenowych.")
    return [str(item or "").strip() for item in parsed if str(item or "").strip()]


def _report_cadastral_context(lat: str | None, lon: str | None) -> tuple[dict | None, str]:
    try:
        lat_float = float(lat or "")
        lon_float = float(lon or "")
    except ValueError:
        return None, ""
    try:
        return lookup_cadastral_parcel(lat_float, lon_float), ""
    except LookupError as exc:
        return None, str(exc)
    except Exception:
        return None, "Nie udało się automatycznie pobrać danych działki ewidencyjnej."


def handle_create_privacy_request(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        result = create_privacy_request(data, core_config.PRIVACY_REQUESTS_DIR)
        http_responses.send_json(handler, 200, result)
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Privacy request creation failed",
            exc,
            public_error="Nie udało się zapisać zgłoszenia prywatności.",
        )


def handle_claim_field_photos(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        photo_ids = data.get("photo_ids") if isinstance(data.get("photo_ids"), list) else []
        photos = list_owner_field_photo_review_items(
            photo_ids,
            data.get("edit_token"),
            core_config.FIELD_PHOTOS_DIR,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_responses.send_json(handler, 200, {"status": "ok", "photos": photos})
    except PermissionError as e:
        http_responses.send_json(handler, 403, {"error": str(e)})
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo owner claim failed",
            exc,
            public_error="Nie udało się odblokować edycji zdjęcia.",
        )


def handle_submit_field_photos(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        photo_ids = data.get("photo_ids") if isinstance(data.get("photo_ids"), list) else []
        result = submit_field_photos_by_owner(
            photo_ids,
            data.get("edit_token"),
            core_config.FIELD_PHOTOS_DIR,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_responses.send_json(handler, 200, result)
    except PermissionError as e:
        http_responses.send_json(handler, 403, {"error": str(e)})
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo owner submit failed",
            exc,
            public_error="Nie udało się wysłać zdjęć do weryfikacji.",
        )


def handle_discard_field_photo_drafts(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        photo_ids = data.get("photo_ids") if isinstance(data.get("photo_ids"), list) else []
        result = discard_field_photo_drafts_by_owner(
            photo_ids,
            data.get("edit_token"),
            core_config.FIELD_PHOTOS_DIR,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_responses.send_json(handler, 200, result)
    except PermissionError as e:
        http_responses.send_json(handler, 403, {"error": str(e)})
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo draft discard failed",
            exc,
            public_error="Nie udało się porzucić szkicu zdjęć.",
        )


def handle_field_photo_report_package(handler) -> None:
    if not access.require_public_feature(
        handler, "report_packages", "Generowanie raportów przez niezalogowanych jest teraz wyłączone."
    ):
        return
    try:
        fields, files = http_request_body.read_multipart_form(handler, core_config.MAX_REPORT_PACKAGE_BODY_BYTES)
        reject_report_package_files(files)
        parcel, parcel_error = _report_cadastral_context(fields.get("lat"), fields.get("lon"))
        result = create_field_photo_report_package(
            fields,
            _report_photo_ids(fields),
            lat=fields.get("lat"),
            lon=fields.get("lon"),
            place_url=fields.get("place_url"),
            parcel=parcel,
            parcel_error=parcel_error,
            field_photos_dir=core_config.FIELD_PHOTOS_DIR,
        )
        http_responses.send_json(handler, 200, result)
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo report package creation failed",
            exc,
            public_error="Nie udało się przygotować raportu ze zdjęć terenowych.",
        )


def handle_create_field_photo(handler) -> None:
    if not access.require_public_feature(
        handler, "photo_uploads", "Dodawanie zdjec przez niezalogowanych jest teraz wylaczone."
    ):
        return
    try:
        fields, files = http_request_body.read_multipart_form(handler, core_config.FIELD_PHOTO_MAX_BODY_BYTES)
        photo_files = [file for file in files if file.field_name == "photo"]
        if len(photo_files) != 1:
            raise ValueError("Dodaj dokładnie jedno zdjęcie w polu 'photo'.")
        is_admin = http_admin_session.is_admin(handler)
        issue_type = fields.get("issue_type")
        if not is_admin and not access.require_public_layer(
            handler,
            access.field_photo_issue_layer_key(issue_type),
            "Ta kategoria zdjec terenowych jest teraz wylaczona dla niezalogowanych.",
        ):
            return
        edit_token = fields.get("edit_token")
        if not is_admin and not str(edit_token or "").strip():
            raise ValueError("Nie udało się przygotować tokenu edycji zdjęcia. Spróbuj ponownie.")
        if not is_admin:
            access.ensure_public_submission_quota(
                handler,
                additional_bytes=len(photo_files[0].data),
                additional_items=1,
            )
        result = save_field_photo(
            photo_files[0],
            core_config.FIELD_PHOTOS_DIR,
            map_lat=fields.get("map_lat"),
            map_lon=fields.get("map_lon"),
            issue_type=issue_type,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
            submission_owner=None if is_admin else access.submission_owner(handler),
            edit_token=None if is_admin else edit_token,
            public_review_status="pending" if is_admin else "draft",
        )
        http_responses.send_json(handler, 200, result)
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo upload failed",
            exc,
            public_error="Nie udało się zapisać zdjęcia terenowego.",
        )


def handle_field_photo_owner_original(handler, photo_id: str) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        file_path, content_type = field_photo_owner_original_asset(
            photo_id,
            data.get("edit_token"),
            core_config.FIELD_PHOTOS_DIR,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_static_files.send_file(handler, file_path, content_type)
    except PermissionError as e:
        http_responses.send_json(handler, 403, {"error": str(e)})
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo owner original lookup failed",
            exc,
            public_error="Nie udało się pobrać oryginału zdjęcia.",
        )


def handle_owner_review_field_photo(handler, photo_id: str) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        result = review_field_photo_by_owner(
            photo_id,
            data.get("edit_token"),
            core_config.FIELD_PHOTOS_DIR,
            redactions=data.get("redactions") or [],
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_responses.send_json(handler, 200, result)
    except PermissionError as e:
        http_responses.send_json(handler, 403, {"error": str(e)})
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo owner review update failed",
            exc,
            public_error="Nie udało się zapisać anonimizacji zdjęcia.",
        )

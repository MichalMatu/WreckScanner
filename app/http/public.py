from app import config
from app.http import access
from app.http import admin_session as http_admin_session
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from app.http import static_files as http_static_files
from core import config as core_config
from core.field_photos import (
    field_photo_owner_original_asset,
    list_owner_field_photo_review_items,
    review_field_photo_by_owner,
    save_field_photo,
)
from core.map_crops import validate_crop_m
from core.privacy_requests import create_privacy_request
from core.report_models import ReportPhotoUpload
from core.report_packages import create_public_report_package, create_report_package
from core.uploads import UploadedFile
from core.wrecks_attachments import (
    attach_field_photos_to_wreck,
    attach_wreck_photos,
    attach_wreck_photos_for_submission,
)
from core.wrecks_save import save_manual_wreck, save_wreck_from_rank


def report_photo_uploads(files: list[UploadedFile]) -> list[ReportPhotoUpload]:
    return [
        ReportPhotoUpload(
            field_name=file.field_name,
            filename=file.filename,
            content_type=file.content_type,
            data=file.data,
        )
        for file in files
        if file.field_name in {"photos", "photos[]"}
    ]


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


def handle_public_report_package(handler, wreck_id: str) -> None:
    try:
        fields, files = http_request_body.read_multipart_form(handler, core_config.MAX_REPORT_PACKAGE_BODY_BYTES)
        photos = report_photo_uploads(files)
        if photos and not access.require_public_feature(
            handler, "photo_uploads", "Dodawanie zdjec przez niezalogowanych jest teraz wylaczone."
        ):
            return
        result = create_public_report_package(wreck_id, fields, photos, core_config.WRECKS_DIR)
        http_responses.send_json(handler, 200, result)
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Public report package creation failed",
            exc,
            public_error="Nie udało się przygotować publicznego pakietu raportu.",
        )


def handle_report_package(handler, wreck_id: str) -> None:
    if not http_admin_session.require_admin(handler):
        return
    try:
        fields, files = http_request_body.read_multipart_form(handler, core_config.MAX_REPORT_PACKAGE_BODY_BYTES)
        photos = report_photo_uploads(files)
        result = create_report_package(wreck_id, fields, photos, core_config.WRECKS_DIR)
        http_responses.send_json(handler, 200, result)
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Admin report package creation failed",
            exc,
            public_error="Nie udało się przygotować pakietu raportu.",
        )


def handle_attach_field_photos_to_wreck(handler, wreck_id: str) -> None:
    if not http_admin_session.require_admin(handler):
        return
    try:
        data = http_request_body.read_json_body(handler)
        photo_ids = data.get("photo_ids") if isinstance(data.get("photo_ids"), list) else []
        result = attach_field_photos_to_wreck(
            wreck_id,
            photo_ids,
            core_config.FIELD_PHOTOS_DIR,
            core_config.WRECKS_DIR,
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
            "Attaching field photos to wreck failed",
            exc,
            public_error="Nie udało się przenieść zdjęć do sprawy pojazdu.",
        )


def handle_wreck_photo_upload(handler, wreck_id: str) -> None:
    if not access.require_public_feature(
        handler, "photo_uploads", "Dodawanie zdjec przez niezalogowanych jest teraz wylaczone."
    ):
        return
    try:
        _, files = http_request_body.read_multipart_form(handler, core_config.MAX_WRECK_PHOTO_BODY_BYTES)
        photos = [file for file in files if file.field_name in {"photos", "photos[]", "photo"}]
        if http_admin_session.is_admin(handler):
            result = attach_wreck_photos(wreck_id, photos, core_config.WRECKS_DIR)
        else:
            additional_bytes = sum(len(file.data) for file in photos)
            access.ensure_public_submission_quota(
                handler,
                additional_bytes=additional_bytes,
                additional_items=max(1, len(photos)),
            )
            result = attach_wreck_photos_for_submission(
                wreck_id,
                photos,
                core_config.WRECKS_DIR,
                submission_owner=access.submission_owner(handler),
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
            "Wreck photo upload failed",
            exc,
            public_error="Nie udało się zapisać zdjęć sprawy pojazdu.",
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
            raise ValueError("Wygeneruj i zachowaj token edycji przed dodaniem zdjęcia.")
        if not is_admin:
            access.ensure_public_submission_quota(
                handler,
                additional_bytes=len(photo_files[0].data),
                additional_items=1,
            )
        ignore_exif_gps = str(fields.get("ignore_exif_gps") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        result = save_field_photo(
            photo_files[0],
            core_config.FIELD_PHOTOS_DIR,
            fallback_lat=fields.get("fallback_lat"),
            fallback_lon=fields.get("fallback_lon"),
            ignore_exif_gps=ignore_exif_gps,
            issue_type=issue_type,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
            submission_owner=None if is_admin else access.submission_owner(handler),
            edit_token=None if is_admin else edit_token,
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


def handle_save_wreck(handler) -> None:
    try:
        data = http_request_body.read_json_body(handler)
        if "rank" in data:
            if not access.require_public_feature(
                handler, "yolo_wrecks", "Dodawanie pinezek z YOLO jest teraz wylaczone dla niezalogowanych."
            ):
                return
        elif not access.require_public_feature(
            handler, "manual_wrecks", "Dodawanie recznych pinezek jest teraz wylaczone dla niezalogowanych."
        ):
            return
        review_status = "approved" if http_admin_session.is_admin(handler) else "pending"
        submission_owner = None if http_admin_session.is_admin(handler) else access.submission_owner(handler)
        if not http_admin_session.is_admin(handler):
            access.ensure_public_submission_quota(handler, additional_bytes=0, additional_items=1)
        if "rank" in data:
            rank = int(data.get("rank"))
            if rank <= 0:
                raise ValueError("Numer kandydata musi być dodatni.")
            result = save_wreck_from_rank(
                rank,
                config.ANALYSIS_DIR,
                config.DOWNLOAD_DATA_DIR,
                core_config.WRECKS_DIR,
                public_review_status=review_status,
                submission_owner=submission_owner,
            )
        else:
            crop_m = validate_crop_m(data.get("cropM", core_config.REVIEW_CROP_M))
            result = save_manual_wreck(
                data.get("lat"),
                data.get("lon"),
                config.DOWNLOAD_DATA_DIR,
                core_config.WRECKS_DIR,
                crop_m=crop_m,
                public_review_status=review_status,
                submission_owner=submission_owner,
            )
        http_responses.send_json(handler, 200, result)
    except (FileNotFoundError, TypeError, ValueError) as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Wreck save failed",
            exc,
            public_error="Nie udało się zapisać sprawy pojazdu.",
        )

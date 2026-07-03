from app.http import admin_session as http_admin_session
from app.http import responses as http_responses
from app.http import static_files as http_static_files
from core import config as core_config
from core.field_photos import field_photo_asset


def handle_admin_photo_original(handler, route: tuple[str, tuple[str, ...]]) -> None:
    if not http_admin_session.require_admin(handler):
        return
    scope, ids = route
    try:
        if scope != "field":
            raise ValueError("Nieprawidłowy zakres zdjęcia.")
        file_path, content_type = field_photo_asset(
            ids[0],
            core_config.FIELD_PHOTOS_DIR,
            "original",
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_static_files.send_file(handler, file_path, content_type)
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Admin photo original lookup failed",
            exc,
            public_error="Nie udało się pobrać prywatnego oryginału zdjęcia.",
        )


def handle_field_photo_asset(handler, route: tuple[str, str]) -> None:
    photo_id, asset = route
    try:
        file_path, content_type = field_photo_asset(
            photo_id,
            core_config.FIELD_PHOTOS_DIR,
            asset,
            private_dir=core_config.PRIVATE_PHOTOS_DIR,
        )
        http_static_files.send_file(handler, file_path, content_type, cache_control="public, max-age=300")
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)})
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Field photo asset lookup failed",
            exc,
            public_error="Nie udało się pobrać pliku zdjęcia terenowego.",
        )

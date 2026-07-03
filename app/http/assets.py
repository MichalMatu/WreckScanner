from app import config
from app.http import admin_session as http_admin_session
from app.http import responses as http_responses
from app.http import static_files as http_static_files
from core import config as core_config
from core.field_photos import field_photo_asset
from core.wrecks import refresh_wreck_report
from core.wrecks_assets import public_wreck_asset, wreck_is_public, wreck_photo_original_asset


def handle_public_wreck_asset(handler, request_path: str, *, include_body: bool = True) -> None:
    parts = [part for part in request_path.strip("/").split("/") if part]
    if len(parts) < 3 or parts[0] != config.WRECKS_ROUTE:
        http_responses.send_json(
            handler,
            404,
            {"error": "Nie znaleziono publicznego pliku sprawy pojazdu."},
            include_body=include_body,
        )
        return
    wreck_id = parts[1]
    relative_path = "/".join(parts[2:])
    if not http_admin_session.is_admin(handler) and not wreck_is_public(wreck_id, core_config.WRECKS_DIR):
        http_responses.send_json(
            handler,
            404,
            {"error": "Nie znaleziono publicznej sprawy pojazdu."},
            include_body=include_body,
        )
        return
    try:
        file_path, content_type = public_wreck_asset(wreck_id, relative_path, core_config.WRECKS_DIR)
        http_static_files.send_file(
            handler,
            file_path,
            content_type,
            cache_control="public, max-age=300",
            include_body=include_body,
        )
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)}, include_body=include_body)
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)}, include_body=include_body)
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Public wreck asset lookup failed",
            exc,
            public_error="Nie udało się pobrać publicznego pliku sprawy pojazdu.",
            include_body=include_body,
        )


def handle_wreck_index(handler, wreck_id: str, *, include_body: bool = True) -> None:
    if not http_admin_session.is_admin(handler) and not wreck_is_public(wreck_id, core_config.WRECKS_DIR):
        http_responses.send_json(
            handler,
            404,
            {"error": "Nie znaleziono publicznej sprawy pojazdu."},
            include_body=include_body,
        )
        return
    try:
        index_path = refresh_wreck_report(wreck_id, core_config.WRECKS_DIR)
        http_static_files.send_file(handler, index_path, "text/html; charset=utf-8", include_body=include_body)
    except FileNotFoundError as e:
        http_responses.send_json(handler, 404, {"error": str(e)}, include_body=include_body)
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)}, include_body=include_body)
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Wreck report refresh failed",
            exc,
            public_error="Nie udało się odświeżyć raportu sprawy pojazdu.",
            include_body=include_body,
        )


def handle_admin_photo_original(handler, route: tuple[str, tuple[str, ...]]) -> None:
    if not http_admin_session.require_admin(handler):
        return
    scope, ids = route
    try:
        if scope == "field":
            file_path, content_type = field_photo_asset(
                ids[0],
                core_config.FIELD_PHOTOS_DIR,
                "original",
                private_dir=core_config.PRIVATE_PHOTOS_DIR,
            )
        else:
            file_path, content_type = wreck_photo_original_asset(ids[0], ids[1], core_config.WRECKS_DIR)
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

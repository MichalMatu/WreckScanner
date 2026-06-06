from app.http import admin_session as http_admin_session
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from core.settings_store import default_app_settings, load_app_settings, save_app_settings


def handle_get_settings(handler) -> None:
    payload = load_app_settings()
    payload["defaults"] = default_app_settings()
    http_responses.send_json(handler, 200, payload)


def handle_save_settings(handler) -> None:
    if not http_admin_session.require_admin(handler):
        return
    try:
        data = http_request_body.read_json_body(handler)
        settings = save_app_settings(data)
        http_responses.send_json(handler, 200, settings)
    except ValueError as e:
        http_responses.send_json(handler, 400, {"error": str(e)})
    except Exception as exc:
        http_responses.send_internal_error(
            handler,
            500,
            "Application settings save failed",
            exc,
            public_error="Nie udało się zapisać ustawień aplikacji.",
        )

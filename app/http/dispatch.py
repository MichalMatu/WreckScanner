from urllib.parse import unquote, urlsplit

from app import config
from app.http import admin as http_admin
from app.http import assets as http_assets
from app.http import health as http_health
from app.http import location as http_location
from app.http import public as http_public
from app.http import public_data as http_public_data
from app.http import request_body as http_request_body
from app.http import responses as http_responses
from app.http import retention as http_retention
from app.http import routes as http_routes
from app.http import settings as http_settings
from app.http import static_files as http_static_files
from app.http import wms_proxy as http_wms_proxy


def handle_options(handler) -> None:
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Request-ID", http_responses.request_id(handler))
    handler.end_headers()


def handle_head(handler) -> bool:
    path = unquote(urlsplit(handler.path).path)
    if http_static_files.handle_web_page(handler, path, include_body=False):
        return True
    wreck_index_wreck_id = http_routes.wreck_index_wreck_id(path)
    if wreck_index_wreck_id:
        http_assets.handle_wreck_index(handler, wreck_index_wreck_id, include_body=False)
        return True
    if path.startswith(f"/{config.WRECKS_ROUTE}/"):
        http_assets.handle_public_wreck_asset(handler, path, include_body=False)
        return True
    if path.startswith("/api/"):
        http_responses.send_api_not_found(handler, include_body=False)
        return True
    return False


def handle_wreck_index_get(handler, path: str) -> bool:
    wreck_index_wreck_id = http_routes.wreck_index_wreck_id(path)
    if not wreck_index_wreck_id:
        return False
    http_assets.handle_wreck_index(handler, wreck_index_wreck_id)
    return True


def handle_static_api_get(handler, path: str) -> bool:
    handlers = {
        "/api/health": lambda: http_health.handle_health(handler),
        "/api/admin/status": lambda: http_admin.handle_admin_status(handler),
        "/api/admin/photos": lambda: http_admin.handle_admin_photos(handler),
        "/api/admin/wrecks": lambda: http_admin.handle_admin_wrecks(handler),
        "/api/admin/privacy-requests": lambda: http_admin.handle_admin_privacy_requests(handler),
        "/api/admin/photo-retention": lambda: http_admin.handle_photo_retention_status(
            handler, http_retention.snapshot()
        ),
        "/api/settings": lambda: http_settings.handle_get_settings(handler),
        "/api/cadastral/identify": lambda: http_public_data.handle_cadastral_identify(handler),
        "/api/surface/features": lambda: http_public_data.handle_surface_features(handler),
        "/api/wrecks": lambda: http_public_data.handle_get_wrecks(handler),
        "/api/field-photos": lambda: http_public_data.handle_field_photos(handler),
    }
    route_handler = handlers.get(path)
    if route_handler is None:
        return False
    route_handler()
    return True


def handle_dynamic_api_get(handler, path: str) -> bool:
    route_handlers = (
        (http_routes.report_package_asset_route, http_assets.handle_report_package_asset),
        (http_routes.public_report_package_asset_route, http_assets.handle_public_report_package_asset),
        (http_routes.admin_photo_original_route, http_assets.handle_admin_photo_original),
        (http_routes.field_photo_asset_route, http_assets.handle_field_photo_asset),
    )
    for route_from_path, route_handler in route_handlers:
        route = route_from_path(path)
        if route:
            route_handler(handler, route)
            return True
    return False


def handle_passthrough_get(handler, path: str) -> bool:
    if handler.path.startswith("/wms_proxy/"):
        http_wms_proxy.handle_wms_proxy(handler)
        return True
    if path.startswith(f"/{config.WRECKS_ROUTE}/"):
        http_assets.handle_public_wreck_asset(handler, path)
        return True
    return False


def handle_get(handler) -> bool:
    path = unquote(urlsplit(handler.path).path)
    if http_static_files.handle_web_page(handler, path):
        return True
    if handle_wreck_index_get(handler, path):
        return True
    if handle_static_api_get(handler, path):
        return True
    if handle_dynamic_api_get(handler, path):
        return True
    if handle_passthrough_get(handler, path):
        return True
    if path.startswith("/api/"):
        http_responses.send_api_not_found(handler)
        return True
    return False


def handle_delete(handler) -> None:
    request_path = unquote(urlsplit(handler.path).path)
    admin_photo_delete_route = http_routes.admin_photo_delete_route(request_path)
    if admin_photo_delete_route:
        http_admin.handle_delete_admin_photo(handler, admin_photo_delete_route)
        return

    if request_path.startswith("/api/field-photos/"):
        http_admin.handle_delete_field_photo(handler, request_path)
        return

    if request_path.startswith("/api/wrecks/"):
        http_admin.handle_delete_wreck(handler, request_path)
        return

    http_responses.send_api_not_found(handler)


def handle_patch(handler) -> None:
    request_path = unquote(urlsplit(handler.path).path)
    admin_wreck_review_route = http_routes.admin_wreck_review_route(request_path)
    if admin_wreck_review_route:
        http_request_body.dispatch_json_request(
            handler, http_admin.handle_review_wreck, handler, admin_wreck_review_route
        )
        return

    admin_photo_review_route = http_routes.admin_photo_review_route(request_path)
    if admin_photo_review_route:
        http_request_body.dispatch_json_request(
            handler, http_admin.handle_review_photo, handler, admin_photo_review_route
        )
        return

    field_photo_location_route = http_routes.field_photo_location_route(request_path)
    if field_photo_location_route:
        http_request_body.dispatch_json_request(
            handler, http_admin.handle_update_field_photo_location, handler, field_photo_location_route
        )
        return

    field_photo_owner_review_route = http_routes.field_photo_owner_review_route(request_path)
    if field_photo_owner_review_route:
        http_request_body.dispatch_json_request(
            handler, http_public.handle_owner_review_field_photo, handler, field_photo_owner_review_route
        )
        return

    admin_privacy_request_route = http_routes.admin_privacy_request_route(request_path)
    if admin_privacy_request_route:
        http_request_body.dispatch_json_request(
            handler, http_admin.handle_update_privacy_request, handler, admin_privacy_request_route
        )
        return

    http_responses.send_api_not_found(handler)


def handle_post(handler) -> None:
    request_path = unquote(urlsplit(handler.path).path)
    if request_path == "/api/admin/login":
        http_request_body.dispatch_json_request(handler, http_admin.handle_admin_login, handler)
        return
    if request_path == "/api/admin/logout":
        http_admin.handle_admin_logout(handler)
        return
    if request_path == "/api/privacy-requests":
        http_request_body.dispatch_json_request(handler, http_public.handle_create_privacy_request, handler)
        return
    if request_path == "/api/field-photos/owner-claim":
        http_request_body.dispatch_json_request(handler, http_public.handle_claim_field_photos, handler)
        return
    if request_path == "/api/admin/photo-retention/run":
        http_request_body.dispatch_json_request(handler, http_retention.handle_run_photo_retention, handler)
        return
    public_report_package_wreck_id = http_routes.public_report_package_wreck_id(request_path)
    if public_report_package_wreck_id:
        http_public.handle_public_report_package(handler, public_report_package_wreck_id)
        return
    report_package_wreck_id = http_routes.report_package_wreck_id(request_path)
    if report_package_wreck_id:
        http_public.handle_report_package(handler, report_package_wreck_id)
        return
    wreck_field_photo_attach_wreck_id = http_routes.wreck_field_photo_attach_wreck_id(request_path)
    if wreck_field_photo_attach_wreck_id:
        http_request_body.dispatch_json_request(
            handler, http_public.handle_attach_field_photos_to_wreck, handler, wreck_field_photo_attach_wreck_id
        )
        return
    wreck_photo_upload_wreck_id = http_routes.wreck_photo_upload_wreck_id(request_path)
    if wreck_photo_upload_wreck_id:
        http_public.handle_wreck_photo_upload(handler, wreck_photo_upload_wreck_id)
        return
    field_photo_owner_original_route = http_routes.field_photo_owner_original_route(request_path)
    if field_photo_owner_original_route:
        http_request_body.dispatch_json_request(
            handler, http_public.handle_field_photo_owner_original, handler, field_photo_owner_original_route
        )
        return
    if request_path == "/api/field-photos":
        http_public.handle_create_field_photo(handler)
        return
    if request_path == "/api/settings":
        http_request_body.dispatch_json_request(handler, http_settings.handle_save_settings, handler)
        return
    if request_path == "/api/inspect":
        http_request_body.dispatch_json_request(handler, http_location.handle_inspect, handler)
        return
    if request_path == "/api/wrecks":
        http_request_body.dispatch_json_request(handler, http_public.handle_save_wreck, handler)
        return
    http_responses.send_api_not_found(handler)

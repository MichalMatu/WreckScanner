from app import config


def path_parts(request_path: str) -> list[str]:
    return [part for part in request_path.strip("/").split("/") if part]


def report_package_wreck_id(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "wrecks" and parts[3] == "report-package":
        return parts[2]
    return None


def public_report_package_wreck_id(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "wrecks" and parts[3] == "public-report-package":
        return parts[2]
    return None


def wreck_photo_upload_wreck_id(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "wrecks" and parts[3] == "photos":
        return parts[2]
    return None


def wreck_field_photo_attach_wreck_id(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if (
        len(parts) == 5
        and parts[0] == "api"
        and parts[1] == "wrecks"
        and parts[3] == "field-photos"
        and parts[4] == "attach"
    ):
        return parts[2]
    return None


def wreck_index_wreck_id(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 3 and parts[0] == config.WRECKS_ROUTE and parts[2] == "index.html":
        return parts[1]
    return None


def field_photo_asset_route(request_path: str) -> tuple[str, str] | None:
    parts = path_parts(request_path)
    if (
        len(parts) == 4
        and parts[0] == "api"
        and parts[1] == "field-photos"
        and parts[3]
        in {
            "public-image",
            "public-thumb",
        }
    ):
        return parts[2], parts[3]
    return None


def admin_photo_original_route(request_path: str) -> tuple[str, tuple[str, ...]] | None:
    parts = path_parts(request_path)
    if len(parts) >= 5 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "photos":
        if parts[3] == "field" and len(parts) == 6 and parts[5] == "original":
            return "field", (parts[4],)
        if parts[3] == "wreck" and len(parts) == 7 and parts[6] == "original":
            return "wreck", (parts[4], parts[5])
    return None


def admin_photo_review_route(request_path: str) -> tuple[str, tuple[str, ...]] | None:
    parts = path_parts(request_path)
    if len(parts) >= 5 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "photos":
        if parts[3] == "field" and len(parts) == 6 and parts[5] == "review":
            return "field", (parts[4],)
        if parts[3] == "wreck" and len(parts) == 7 and parts[6] == "review":
            return "wreck", (parts[4], parts[5])
    return None


def admin_photo_delete_route(request_path: str) -> tuple[str, tuple[str, ...]] | None:
    parts = path_parts(request_path)
    if len(parts) >= 5 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "photos":
        if parts[3] == "field" and len(parts) == 5:
            return "field", (parts[4],)
        if parts[3] == "wreck" and len(parts) == 6:
            return "wreck", (parts[4], parts[5])
    return None


def admin_wreck_review_route(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 5 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "wrecks" and parts[4] == "review":
        return parts[3]
    return None


def field_photo_location_route(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "field-photos" and parts[3] == "location":
        return parts[2]
    return None


def field_photo_owner_original_route(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "field-photos" and parts[3] == "owner-original":
        return parts[2]
    return None


def field_photo_owner_review_route(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "field-photos" and parts[3] == "owner-review":
        return parts[2]
    return None


def admin_privacy_request_route(request_path: str) -> str | None:
    parts = path_parts(request_path)
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "privacy-requests":
        return parts[3]
    return None


def report_package_asset_route(request_path: str) -> tuple[str, str, str] | None:
    parts = path_parts(request_path)
    if (
        len(parts) == 5
        and parts[0] == "api"
        and parts[1] == "report-packages"
        and (parts[4].endswith(".zip") or parts[4].endswith(".pdf"))
    ):
        return parts[2], parts[3], parts[4]
    return None


def public_report_package_asset_route(request_path: str) -> tuple[str, str, str] | None:
    parts = path_parts(request_path)
    if (
        len(parts) == 5
        and parts[0] == "api"
        and parts[1] == "public-report-packages"
        and (parts[4].endswith(".zip") or parts[4].endswith(".pdf"))
    ):
        return parts[2], parts[3], parts[4]
    return None

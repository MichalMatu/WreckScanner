def path_parts(request_path: str) -> list[str]:
    return [part for part in request_path.strip("/").split("/") if part]


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
    if (
        len(parts) == 6
        and parts[0] == "api"
        and parts[1] == "admin"
        and parts[2] == "photos"
        and parts[3] == "field"
        and parts[5] == "original"
    ):
        return "field", (parts[4],)
    return None


def admin_photo_review_route(request_path: str) -> tuple[str, tuple[str, ...]] | None:
    parts = path_parts(request_path)
    if (
        len(parts) == 6
        and parts[0] == "api"
        and parts[1] == "admin"
        and parts[2] == "photos"
        and parts[3] == "field"
        and parts[5] == "review"
    ):
        return "field", (parts[4],)
    return None


def admin_photo_delete_route(request_path: str) -> tuple[str, tuple[str, ...]] | None:
    parts = path_parts(request_path)
    if len(parts) == 5 and parts[0] == "api" and parts[1] == "admin" and parts[2] == "photos" and parts[3] == "field":
        return "field", (parts[4],)
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

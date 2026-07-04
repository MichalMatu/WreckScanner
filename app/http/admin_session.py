from http import cookies

from app import config
from app.http import auth
from app.http import responses as http_responses


def admin_token_from_cookie(handler) -> str | None:
    raw_cookie = handler.headers.get("Cookie", "")
    if not raw_cookie:
        return None
    jar = cookies.SimpleCookie()
    try:
        jar.load(raw_cookie)
    except cookies.CookieError:
        return None
    morsel = jar.get(config.ADMIN_COOKIE_NAME)
    return morsel.value if morsel else None


def is_admin(handler) -> bool:
    return auth.valid_admin_token(admin_token_from_cookie(handler))


def is_local_request_host(handler) -> bool:
    raw_host = handler.headers.get("Host", "").strip().lower()
    if raw_host.startswith("[") and "]" in raw_host:
        host = raw_host.split("]", 1)[0].strip("[]")
    else:
        host = raw_host.split(":", 1)[0]
    return host in {"localhost", "127.0.0.1", "::1"}


def admin_cookie_header(handler, value: str, *, max_age: int) -> str:
    attrs = [
        f"{config.ADMIN_COOKIE_NAME}={value}",
        "HttpOnly",
        "SameSite=Lax",
        "Path=/",
        f"Max-Age={max_age}",
    ]
    if config.ADMIN_COOKIE_SECURE and not is_local_request_host(handler):
        attrs.insert(2, "Secure")
    return "; ".join(attrs)


def require_admin(handler) -> bool:
    if is_admin(handler):
        return True
    if not auth.admin_enabled():
        http_responses.send_json(
            handler,
            503,
            {
                "error": "Panel administratora nie ma ustawionego hasla. Ustaw WRECKSCANNER_ADMIN_PASSWORD albo plik .admin_password."
            },
        )
        return False
    http_responses.send_json(handler, 401, {"error": "Wymagane logowanie administratora."})
    return False

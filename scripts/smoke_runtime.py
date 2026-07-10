#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class SmokeResponse:
    url: str
    status: int
    headers: object
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def validated_base_url(base_url: str) -> str:
    text = str(base_url or "").strip().rstrip("/")
    try:
        parsed = urlsplit(text)
        _ = parsed.port
    except ValueError as exc:
        raise SmokeFailure("Base URL smoke testu jest nieprawidlowy.") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SmokeFailure("Base URL smoke testu musi uzywac schematu http albo https i zawierac host.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SmokeFailure("Base URL smoke testu nie moze zawierac danych logowania, query ani fragmentu.")
    return text


def smoke_url(base_url: str, path: str) -> str:
    return f"{validated_base_url(base_url)}/{path.lstrip('/')}"


def request(base_url: str, path: str, *, timeout: float = 5.0, method: str = "GET") -> SmokeResponse:
    url = smoke_url(base_url, path)
    req = Request(url, method=method, headers={"User-Agent": "WreckScannerRuntimeSmoke/1"})
    try:
        # smoke_url accepts only explicit HTTP(S) URLs with a host, so other urllib schemes cannot reach this call.
        with urlopen(req, timeout=timeout) as response:  # nosec B310
            return SmokeResponse(url=url, status=response.status, headers=response.headers, body=response.read())
    except HTTPError as exc:
        return SmokeResponse(url=url, status=exc.code, headers=exc.headers, body=exc.read())
    except URLError as exc:
        raise SmokeFailure(f"{path}: nie można połączyć się z serwerem ({exc.reason}).") from exc


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def expect_status(response: SmokeResponse, status: int, label: str) -> None:
    expect(response.status == status, f"{label}: oczekiwano HTTP {status}, otrzymano {response.status}.")


def expect_header(response: SmokeResponse, key: str, value: str, label: str) -> None:
    actual = response.headers.get(key)
    expect(actual == value, f"{label}: nagłówek {key} ma wartość {actual!r}, oczekiwano {value!r}.")


def expect_security_headers(response: SmokeResponse, label: str) -> None:
    content_security_policy = response.headers.get("Content-Security-Policy", "")
    expect("object-src 'none'" in content_security_policy, f"{label}: brak restrykcyjnego CSP.")
    expect_header(response, "Permissions-Policy", "camera=(), geolocation=(), microphone=()", label)
    expect_header(response, "X-Content-Type-Options", "nosniff", label)
    expect_header(response, "Referrer-Policy", "same-origin", label)
    expect_header(response, "X-Frame-Options", "SAMEORIGIN", label)


def expect_json(response: SmokeResponse, label: str) -> dict:
    content_type = response.headers.get("Content-Type", "")
    expect("application/json" in content_type, f"{label}: odpowiedź nie jest JSON ({content_type!r}).")
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"{label}: nieprawidłowy JSON: {exc}.") from exc
    expect(isinstance(payload, dict), f"{label}: JSON musi być obiektem.")
    return payload


def check_landing(base_url: str, timeout: float) -> str:
    response = request(base_url, "/", timeout=timeout)
    expect_status(response, 200, "landing")
    expect_security_headers(response, "landing")
    content_type = response.headers.get("Content-Type", "")
    expect("text/html" in content_type, f"landing: oczekiwano HTML, otrzymano {content_type!r}.")
    html = response.text
    for marker in (
        'id="map"',
        'id="panel-add-field-photo"',
        'onclick="openFieldPhotoUploadFromPanel()"',
        '<script src="/app/startup.js"></script>',
    ):
        expect(marker in html, f"landing: brakuje markera {marker!r}.")
    for retired_marker in ('class="social-links"', 'href="https://www.facebook.com/WreckScanner/"'):
        expect(retired_marker not in html, f"landing: znaleziono wycofany marker {retired_marker!r}.")
    return "landing"


def check_static_asset(base_url: str, path: str, timeout: float) -> str:
    response = request(base_url, path, timeout=timeout)
    expect_status(response, 200, path)
    expect_security_headers(response, path)
    cache_control = response.headers.get("Cache-Control", "")
    expect("no-store" in cache_control.lower(), f"{path}: asset aplikacji musi mieć Cache-Control: no-store.")
    expect(response.body, f"{path}: pusty asset.")
    return path


def check_health(base_url: str, timeout: float) -> str:
    live_response = request(base_url, "/api/health/live", timeout=timeout)
    expect_status(live_response, 200, "health live")
    expect_security_headers(live_response, "health live")
    live_payload = expect_json(live_response, "health live")
    expect(live_payload.get("status") == "ok", "health live: status JSON musi być 'ok'.")

    ready_response = request(base_url, "/api/health/ready", timeout=timeout)
    expect_status(ready_response, 200, "health ready")
    expect_security_headers(ready_response, "health ready")
    ready_payload = expect_json(ready_response, "health ready")
    expect(ready_payload.get("status") == "ok", "health ready: status JSON musi być 'ok'.")
    expect(isinstance(ready_payload.get("checks"), dict), "health ready: pole 'checks' musi być obiektem.")
    return "health"


def check_public_json_list(base_url: str, path: str, key: str, timeout: float) -> str:
    response = request(base_url, path, timeout=timeout)
    expect_status(response, 200, path)
    expect_security_headers(response, path)
    payload = expect_json(response, path)
    expect(payload.get("status") == "ok", f"{path}: status JSON musi być 'ok'.")
    expect(isinstance(payload.get(key), list), f"{path}: pole {key!r} musi być listą.")
    return path


def check_json_404(base_url: str, timeout: float) -> str:
    response = request(base_url, "/api/__runtime_smoke_missing__", timeout=timeout)
    expect_status(response, 404, "api 404")
    expect_security_headers(response, "api 404")
    payload = expect_json(response, "api 404")
    expect("error" in payload, "api 404: brak publicznego pola error.")
    expect("request_id" in payload, "api 404: brak request_id.")
    expect("Traceback" not in response.text, "api 404: odpowiedź ujawnia traceback.")
    return "api 404"


def run_smoke(base_url: str, *, timeout: float = 5.0) -> list[str]:
    checks = [
        check_landing(base_url, timeout),
        check_static_asset(base_url, "/styles.css", timeout),
        check_static_asset(base_url, "/styles/panel.css", timeout),
        check_static_asset(base_url, "/i18n/pl.js", timeout),
        check_static_asset(base_url, "/i18n/en.js", timeout),
        check_static_asset(base_url, "/i18n.js", timeout),
        check_static_asset(base_url, "/app.js", timeout),
        check_static_asset(base_url, "/app/api.js", timeout),
        check_static_asset(base_url, "/app/field_photo_upload.js", timeout),
        check_static_asset(base_url, "/app/settings.js", timeout),
        check_health(base_url, timeout),
        check_public_json_list(base_url, "/api/field-photos", "photos", timeout),
        check_json_404(base_url, timeout),
    ]
    return checks


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime smoke test for a running WreckScanner server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="Base URL of the running app.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-request timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON result.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    try:
        checks = run_smoke(args.base_url, timeout=args.timeout)
    except SmokeFailure as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"status": "ok", "checks": checks}, ensure_ascii=False))
    else:
        for check in checks:
            print(f"OK {check}")
        print("OK: runtime smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

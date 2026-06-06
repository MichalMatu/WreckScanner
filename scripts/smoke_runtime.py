#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
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


def smoke_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def request(base_url: str, path: str, *, timeout: float = 5.0, method: str = "GET") -> SmokeResponse:
    url = smoke_url(base_url, path)
    req = Request(url, method=method, headers={"User-Agent": "WreckScannerRuntimeSmoke/1"})
    try:
        with urlopen(req, timeout=timeout) as response:
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
    expect(response.body, f"{path}: pusty asset.")
    return path


def check_health(base_url: str, timeout: float) -> str:
    response = request(base_url, "/api/health", timeout=timeout)
    expect_status(response, 200, "health")
    expect_security_headers(response, "health")
    payload = expect_json(response, "health")
    expect(payload.get("status") in {"ok", "degraded"}, f"health: nieprawidłowy status {payload.get('status')!r}.")
    for key in ("pressure", "pipeline", "wms_tile_cache"):
        expect(isinstance(payload.get(key), dict), f"health: pole {key!r} musi być obiektem.")
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
        check_static_asset(base_url, "/app.js", timeout),
        check_static_asset(base_url, "/app/api.js", timeout),
        check_static_asset(base_url, "/app/field_photo_upload.js", timeout),
        check_static_asset(base_url, "/app/settings.js", timeout),
        check_health(base_url, timeout),
        check_public_json_list(base_url, "/api/wrecks", "wrecks", timeout),
        check_public_json_list(base_url, "/api/field-photos", "photos", timeout),
        check_json_404(base_url, timeout),
    ]
    return checks


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime smoke test for a running WreckScanner server.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the running app.")
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

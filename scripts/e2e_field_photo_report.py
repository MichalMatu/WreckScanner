#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from PIL import Image, ImageStat  # noqa: E402

from core import config  # noqa: E402


class E2EFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: object
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class HttpClient:
    def __init__(self, base_url: str, *, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        request = Request(
            self.url(path),
            data=body,
            method=method,
            headers={
                "User-Agent": "WreckScannerE2E/1",
                **(headers or {}),
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return HttpResult(status=response.status, headers=response.headers, body=response.read())
        except HTTPError as exc:
            return HttpResult(status=exc.code, headers=exc.headers, body=exc.read())
        except URLError as exc:
            raise E2EFailure(f"{path}: nie można połączyć się z serwerem ({exc.reason}).") from exc

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json", **(headers or {})}
        response = self.request(method, path, body=body, headers=headers)
        if response.status != expected_status:
            raise E2EFailure(f"{method} {path}: HTTP {response.status}, oczekiwano {expected_status}: {response.text}")
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise E2EFailure(f"{method} {path}: odpowiedź nie jest JSON ({content_type}).")
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise E2EFailure(f"{method} {path}: nieprawidłowy JSON: {exc}.") from exc
        if not isinstance(data, dict):
            raise E2EFailure(f"{method} {path}: JSON musi być obiektem.")
        return data


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise E2EFailure(message)


def expect_checked_at(value: Any, message: str) -> None:
    text = str(value or "")
    expect(text.startswith("20") and "T" in text, message)


def read_admin_password(path: Path) -> str:
    try:
        password = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise E2EFailure(f"Brak pliku hasła administratora: {path}.") from exc
    if not password:
        raise E2EFailure(f"Plik hasła administratora jest pusty: {path}.")
    return password


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (96, 72), (82, 124, 164))
    image.save(buffer, "JPEG", quality=88)
    return buffer.getvalue()


def multipart_body(
    fields: dict[str, Any],
    files: list[tuple[str, str, str, bytes]],
) -> tuple[str, bytes]:
    boundary = f"----WreckScannerE2E{int(time.time() * 1000)}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for field_name, filename, content_type, data in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'
                ).encode(),
                data,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(chunks)


def login_admin(client: HttpClient, password: str) -> None:
    data = client.json("POST", "/api/admin/login", payload={"password": password})
    expect(
        data.get("status") == "ok" and data.get("authenticated") is True, "Logowanie administratora nie powiodło się."
    )


def upload_field_photo(client: HttpClient, *, lat: float, lon: float) -> str:
    content_type, body = multipart_body(
        {
            "map_lat": f"{lat:.6f}",
            "map_lon": f"{lon:.6f}",
            "issue_type": "vehicle",
            "vehicle_insurance_status": "uninsured",
        },
        [("photo", "wreckscanner_e2e.jpg", "image/jpeg", image_bytes())],
    )
    data = client.json("POST", "/api/field-photos", body=body, headers={"Content-Type": content_type})
    photo = data.get("photo") if isinstance(data.get("photo"), dict) else {}
    photo_id = str(photo.get("id") or "")
    expect(photo_id.startswith("photo_"), "Upload nie zwrócił identyfikatora zdjęcia.")
    expect(photo.get("public_review_status") == "pending", "Upload admina powinien utworzyć zdjęcie pending.")
    expect(photo.get("vehicle_insurance_status") == "uninsured", "Upload nie zapisał statusu OC/UFG.")
    expect_checked_at(photo.get("vehicle_insurance_checked_at"), "Upload nie zapisał daty sprawdzenia OC/UFG.")
    return photo_id


def approve_field_photo(client: HttpClient, photo_id: str) -> dict[str, Any]:
    data = client.json(
        "PATCH",
        f"/api/admin/photos/field/{quote(photo_id)}/review",
        payload={"public_review_status": "approved", "redactions": [], "vehicle_insurance_status": "insured"},
    )
    photo = data.get("photo") if isinstance(data.get("photo"), dict) else {}
    expect(photo.get("id") == photo_id, "Review nie zwrócił zatwierdzonego zdjęcia.")
    expect(photo.get("public_review_status") == "approved", "Zdjęcie po review nie jest approved.")
    expect(photo.get("vehicle_insurance_status") == "insured", "Review nie zaktualizował statusu OC/UFG.")
    expect_checked_at(photo.get("vehicle_insurance_checked_at"), "Review nie zapisał daty sprawdzenia OC/UFG.")
    expect(photo.get("public_image"), "Zatwierdzone zdjęcie nie ma public_image.")
    expect(photo.get("public_thumb"), "Zatwierdzone zdjęcie nie ma public_thumb.")
    return photo


def public_photo(client: HttpClient, photo_id: str) -> dict[str, Any]:
    data = client.json("GET", "/api/field-photos")
    photos = data.get("photos") if isinstance(data.get("photos"), list) else []
    matches = [photo for photo in photos if isinstance(photo, dict) and photo.get("id") == photo_id]
    expect(matches, "Zatwierdzone zdjęcie nie jest widoczne w publicznym /api/field-photos.")
    photo = matches[0]
    for key in ("edit_token", "edit_token_hash", "edit_token_salt", "private_original_file", "submission_owner"):
        expect(key not in photo, f"Publiczne API ujawnia prywatne pole {key}.")
    expect(photo.get("issue_type") == "vehicle", "Publiczne zdjęcie nie ma typu vehicle.")
    expect(photo.get("vehicle_insurance_status") == "insured", "Publiczne API nie zwraca statusu OC/UFG.")
    expect_checked_at(photo.get("vehicle_insurance_checked_at"), "Publiczne API nie zwraca daty sprawdzenia OC/UFG.")
    expect(photo.get("public_image") and photo.get("public_thumb"), "Publiczne zdjęcie nie ma publicznych assetów.")
    return photo


def report_fields(photo_id: str, *, lat: float, lon: float) -> dict[str, str]:
    return {
        "reporter_name": "WreckScanner E2E",
        "reporter_address": "Testowa 1, 50-000 Wrocław",
        "reporter_phone": "000 000 000",
        "reporter_email": "e2e@example.test",
        "location_description": "Automatyczny test E2E WreckScanner.",
        "observed_at": "2026-07-04T09:00",
        "vehicle_description": "Zdjęcie testowe dodane i usuwane przez E2E.",
        "photo_ids": json.dumps([photo_id]),
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "crop_m": "5",
    }


def create_report_pdf(client: HttpClient, photo_id: str, *, lat: float, lon: float) -> dict[str, Any]:
    content_type, body = multipart_body(report_fields(photo_id, lat=lat, lon=lon), [])
    data = client.json(
        "POST",
        "/api/field-photo-reports/report-pdf",
        body=body,
        headers={"Content-Type": content_type},
        expected_status=200,
    )
    expect(data.get("status") == "ok", f"Raport nie zwrócił statusu ok: {data!r}")
    expect(data.get("photo_count") == 1, "Raport powinien zawierać jedno zatwierdzone zdjęcie.")
    pdf_bytes = base64.b64decode(str(data.get("pdf_base64") or ""))
    expect(pdf_bytes[:5] == b"%PDF-", "PDF raportu nie ma poprawnego nagłówka.")
    expect("zip_base64" not in data, "Endpoint PDF nie powinien zwracać ZIP-a.")
    expect("body" not in data, "Endpoint PDF nie powinien zwracać osobnego tekstu zgłoszenia.")
    return data


def screenshot_has_pixels(path: Path) -> None:
    with Image.open(path) as image:
        expect(image.size[0] >= 320 and image.size[1] >= 480, f"Screenshot {path} ma podejrzany rozmiar {image.size}.")
        stat = ImageStat.Stat(image.convert("RGB"))
        expect(sum(stat.stddev) > 5.0, f"Screenshot {path} wygląda na pusty.")


def chromium_bin() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


def capture_map_screenshot(
    *,
    base_url: str,
    photo_id: str,
    viewport: str,
    size: tuple[int, int],
    output_dir: Path,
    profile_dir: Path,
    timeout: float,
) -> Path:
    binary = chromium_bin()
    if not binary:
        raise E2EFailure("Nie znaleziono Chromium/Chrome do screenshotów desktop/mobile.")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"e2e-map-{viewport}.png"
    url = f"{base_url}/?photo={quote(photo_id)}"
    command = [
        binary,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--ignore-certificate-errors",
        f"--user-data-dir={profile_dir}",
        f"--window-size={size[0]},{size[1]}",
        "--virtual-time-budget=8000",
        f"--screenshot={output_path}",
        url,
    ]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise E2EFailure(f"Chromium screenshot {viewport} nie powiódł się: {completed.stderr.strip()}")
    if not output_path.exists():
        raise E2EFailure(f"Chromium nie zapisał screenshotu {output_path}.")
    screenshot_has_pixels(output_path)
    return output_path


def prime_chromium_profile(*, base_url: str, profile_dir: Path, timeout: float) -> None:
    binary = chromium_bin()
    if not binary:
        raise E2EFailure("Nie znaleziono Chromium/Chrome do przygotowania profilu E2E.")
    command = [
        binary,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--ignore-certificate-errors",
        f"--user-data-dir={profile_dir}",
        "--virtual-time-budget=1000",
        "--dump-dom",
        base_url,
    ]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise E2EFailure(f"Chromium profile prime nie powiódł się: {completed.stderr.strip()}")


def delete_photo(client: HttpClient, photo_id: str) -> None:
    response = client.request("DELETE", f"/api/field-photos/{quote(photo_id)}")
    if response.status not in {200, 404}:
        raise E2EFailure(f"Cleanup DELETE {photo_id}: HTTP {response.status}: {response.text}")


def assert_photo_deleted(client: HttpClient, photo_id: str) -> None:
    data = client.json("GET", "/api/field-photos")
    photos = data.get("photos") if isinstance(data.get("photos"), list) else []
    expect(
        not any(isinstance(photo, dict) and photo.get("id") == photo_id for photo in photos),
        "Testowe zdjęcie zostało w publicznym API.",
    )
    expect(
        not (ROOT_DIR / config.FIELD_PHOTOS_DIR / photo_id).exists(),
        "Katalog testowego zdjęcia został w zdjecia_terenowe.",
    )
    expect(
        not (ROOT_DIR / config.PRIVATE_PHOTOS_DIR / "field_photos" / photo_id).exists(),
        "Prywatny oryginał testowego zdjęcia został na dysku.",
    )


def assert_no_persistent_report_artifacts() -> None:
    expect(not (ROOT_DIR / "prywatne_zgloszenia").exists(), "Raport E2E odtworzył trwały katalog prywatne_zgloszenia.")


def run_e2e(args: argparse.Namespace) -> list[str]:
    client = HttpClient(args.base_url, timeout=args.timeout)
    photo_id = ""
    checks: list[str] = []
    try:
        login_admin(client, read_admin_password(args.admin_password_file))
        checks.append("admin-login")
        photo_id = upload_field_photo(client, lat=args.lat, lon=args.lon)
        checks.append(f"upload:{photo_id}")
        approve_field_photo(client, photo_id)
        checks.append("admin-review")
        public_photo(client, photo_id)
        checks.append("public-map-contract")
        create_report_pdf(client, photo_id, lat=args.lat, lon=args.lon)
        checks.append("report-pdf")
        assert_no_persistent_report_artifacts()
        checks.append("no-persistent-report-artifacts")
        if not args.skip_browser:
            with TemporaryDirectory(prefix="wreckscanner-e2e-chromium-") as profile_name:
                profile_dir = Path(profile_name)
                prime_chromium_profile(
                    base_url=args.base_url.rstrip("/"),
                    profile_dir=profile_dir,
                    timeout=args.browser_timeout,
                )
                desktop = capture_map_screenshot(
                    base_url=args.base_url.rstrip("/"),
                    photo_id=photo_id,
                    viewport="desktop",
                    size=(1366, 900),
                    output_dir=args.output_dir,
                    profile_dir=profile_dir,
                    timeout=args.browser_timeout,
                )
                mobile = capture_map_screenshot(
                    base_url=args.base_url.rstrip("/"),
                    photo_id=photo_id,
                    viewport="mobile",
                    size=(390, 844),
                    output_dir=args.output_dir,
                    profile_dir=profile_dir,
                    timeout=args.browser_timeout,
                )
            checks.append(f"screenshot:{desktop}")
            checks.append(f"screenshot:{mobile}")
    finally:
        if photo_id:
            delete_photo(client, photo_id)
            assert_photo_deleted(client, photo_id)
            assert_no_persistent_report_artifacts()
            checks.append("cleanup")
    return checks


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2E: field photo upload, review, map contract and report PDF.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--admin-password-file", type=Path, default=ROOT_DIR / ".admin_password")
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR / "analiza")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--browser-timeout", type=float, default=45.0)
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--lat", type=float, default=51.109)
    parser.add_argument("--lon", type=float, default=17.032)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    try:
        checks = run_e2e(args)
    except (E2EFailure, TimeoutError, subprocess.TimeoutExpired) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"E2E FAILED: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"status": "ok", "checks": checks}, ensure_ascii=False))
    else:
        for check in checks:
            print(f"OK {check}")
        print("OK: field photo report E2E passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

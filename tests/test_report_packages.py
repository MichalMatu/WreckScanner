import base64
import io
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

import core.report_pdf as report_pdf
from app.http import public as http_public
from app.http.public import reject_report_package_files
from core.report_assets import report_package_download_name
from core.report_models import safe_report_url, validate_report_fields
from core.report_packages import create_field_photo_report_package
from core.uploads import UploadedFile


def image_bytes(fmt: str = "JPEG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 24), (120, 80, 40)).save(out, fmt)
    return out.getvalue()


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def valid_fields() -> dict[str, str]:
    return {
        "reporter_name": "Jan Kowalski",
        "reporter_address": "ul. Testowa 1, Wrocław",
        "reporter_phone": "500 600 700",
        "reporter_email": "jan@example.com",
        "location_description": "ul. Długa 10, przy parkingu",
        "observed_at": "2026-06-02T12:30",
        "vehicle_description": "Pojazd zabrudzony, długo stoi w tym samym miejscu.",
    }


def fake_save_location_crops(lat: float, lon: float, output_dir: Path, **kwargs):
    output_dir.mkdir(parents=True, exist_ok=True)
    for year in (2024, 2025):
        (output_dir / f"{year}.jpg").write_bytes(image_bytes())
    crop_m = float(kwargs.get("crop_m", 7.5))
    return (
        [{"label": "2024", "file": "2024.jpg"}, {"label": "2025", "file": "2025.jpg"}],
        {
            "center_lat": lat,
            "center_lon": lon,
            "crop_meters": crop_m,
            "years": [2024, 2025],
            "source": "wroclaw_wms_location_crops",
        },
    )


def create_field_photo_fixture(
    root: Path, *, issue_type: str = "vehicle", status: str = "approved"
) -> tuple[Path, str]:
    field_dir = root / "zdjecia_terenowe"
    photo_id = "photo_20260604T201000Z_11111111"
    photo_dir = field_dir / photo_id
    photo_dir.mkdir(parents=True, exist_ok=True)
    (photo_dir / "public.jpg").write_bytes(image_bytes())
    (photo_dir / "public_thumb.jpg").write_bytes(image_bytes())
    write_json(
        photo_dir / "record.json",
        {
            "id": photo_id,
            "created_at": "2026-06-04T20:10:00Z",
            "original_filename": "teren.jpg",
            "content_type": "image/jpeg",
            "format": "JPEG",
            "size_bytes": len(image_bytes()),
            "image_width": 32,
            "image_height": 24,
            "issue_type": issue_type,
            "lat": 51.1,
            "lon": 17.2,
            "coordinate_source": "map",
            "captured_at": "2026-06-04T20:00:00",
            "private_original_file": f"field_photos/{photo_id}/original.jpg",
            "public_review_status": status,
            "redactions": [],
            "reviewed_at": "2026-06-04T20:12:00Z" if status == "approved" else None,
            "public_image_file": "public.jpg",
            "public_thumb_file": "public_thumb.jpg",
            "public_width": 32,
            "public_height": 24,
            "links": {},
        },
    )
    return field_dir, photo_id


class ReportPackageTests(unittest.TestCase):
    def test_report_package_download_name_uses_readable_timestamp(self):
        self.assertEqual(
            report_package_download_name("report_20260702T142516Z_0b05a053", "zip"),
            "raport_20260702_142516.zip",
        )
        self.assertEqual(
            report_package_download_name("report_20260702T142516Z_0b05a053", "pdf"),
            "raport_20260702_142516.pdf",
        )
        with self.assertRaisesRegex(ValueError, "typ pliku"):
            report_package_download_name("report_20260702T142516Z_0b05a053", "html")

    def test_validate_report_fields_requires_clean_email_and_short_values(self):
        fields = valid_fields()
        fields["reporter_name"] = "  Jan\x00 Kowalski  "

        validated = validate_report_fields(fields)

        self.assertEqual(validated["reporter_name"], "Jan Kowalski")

        with self.assertRaisesRegex(ValueError, "adres e-mail"):
            validate_report_fields({**valid_fields(), "reporter_email": "jan.example.com"})

        with self.assertRaisesRegex(ValueError, "wymagane pola"):
            validate_report_fields({**valid_fields(), "reporter_phone": ""})

        with self.assertRaisesRegex(ValueError, "zbyt długie"):
            validate_report_fields({**valid_fields(), "vehicle_description": "x" * 4001})

        self.assertEqual(
            safe_report_url("https://wreckscanner.pl/?lat=51&lon=17"),
            "https://wreckscanner.pl/?lat=51&lon=17",
        )
        self.assertEqual(safe_report_url("javascript:alert(1)"), "")

    def test_reject_report_package_files_rejects_uploaded_files(self):
        with self.assertRaisesRegex(ValueError, "Zdjęcia do zgłoszenia"):
            reject_report_package_files([UploadedFile("photos", "car.jpg", "image/jpeg", b"x")])

        reject_report_package_files([])

    def test_report_cadastral_context_is_best_effort(self):
        with patch("app.http.public.lookup_cadastral_parcel", return_value={"parcel_number": "87"}):
            parcel, error = http_public._report_cadastral_context("51.1", "17.2")

        self.assertEqual(parcel, {"parcel_number": "87"})
        self.assertEqual(error, "")

        with patch("app.http.public.lookup_cadastral_parcel", side_effect=RuntimeError("upstream")):
            parcel, error = http_public._report_cadastral_context("51.1", "17.2")

        self.assertIsNone(parcel)
        self.assertIn("automatycznie pobrać", error)

    def test_create_field_photo_report_package_uses_field_photo_group_without_archived_case(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir, photo_id = create_field_photo_fixture(root)
            place_url = f"https://wreckscanner.pl/?lat=51.100000&lon=17.200000&z=20&photo={photo_id}"
            parcel = {
                "parcel_number": "87",
                "parcel_id": "026401_1.0022.AR_27.87",
                "district": "Południe",
                "municipality": "Wrocław",
                "county": "Wrocław",
                "voivodeship": "dolnośląskie",
                "area_ha": "0.5964",
                "registry_group": "7.1",
                "contour": "B",
                "published_at": "2026-06-05",
            }

            with patch("core.report_evidence.save_location_crops", side_effect=fake_save_location_crops):
                result = create_field_photo_report_package(
                    valid_fields(),
                    [photo_id],
                    lat=51.1,
                    lon=17.2,
                    place_url=place_url,
                    parcel=parcel,
                    field_photos_dir=field_dir,
                )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["zip_filename"], report_package_download_name(result["package_id"], "zip"))
            self.assertNotIn("zip_url", result)
            self.assertNotIn("pdf_url", result)
            self.assertIn(place_url, result["body"])
            self.assertIn("Dane działki ewidencyjnej", result["body"])
            self.assertIn("- Numer działki: 87", result["body"])
            self.assertIn("- Typ terenu: B - tereny mieszkaniowe", result["body"])
            self.assertNotIn("- Powierzchnia:", result["body"])
            self.assertNotIn("- Kontur:", result["body"])
            self.assertNotIn("- Użytek:", result["body"])
            self.assertNotIn("Geoportal działki", result["body"])
            self.assertNotIn("identifyParcel", result["body"])
            pdf_link = report_pdf._paragraph_text(place_url)
            self.assertIn("Otwórz miejsce w WreckScanner", pdf_link)
            self.assertIn("https://wreckscanner.pl/?lat=51.100000&amp;lon=17.200000", pdf_link)
            pdf_bytes = base64.b64decode(result["pdf_base64"])
            self.assertEqual(pdf_bytes[:5], b"%PDF-")
            self.assertIn(b"https://wreckscanner.pl/?lat=51.100000", pdf_bytes)
            self.assertFalse((root / "zidentyfikowane_wraki").exists())
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["zip_base64"]))) as archive:
                names = set(archive.namelist())
                self.assertIn("zgloszenie.txt", names)
                self.assertIn("raport.html", names)
                self.assertIn(f"photos/{photo_id}/public.jpg", names)
                self.assertIn(f"photos/{photo_id}/public_thumb.jpg", names)
                self.assertIn("miniatury_historyczne/2024.jpg", names)
                self.assertIn("miniatury_historyczne/2025.jpg", names)
                self.assertNotIn(f"field_photos/{photo_id}/original.jpg", names)
                self.assertFalse(any(name.endswith(".json") for name in names))
                text = archive.read("zgloszenie.txt").decode("utf-8")
                report_html = archive.read("raport.html").decode("utf-8")
                self.assertIn(place_url, text)
                self.assertIn("Identyfikator działki: 026401_1.0022.AR_27.87", text)
                self.assertIn("Typ terenu: B - tereny mieszkaniowe", text)
                self.assertNotIn("Powierzchnia:", text)
                self.assertNotIn("Kontur:", text)
                self.assertNotIn("Użytek:", text)
                self.assertNotIn("Geoportal działki", text)
                self.assertIn("Link do miejsca w WreckScanner", report_html)
                self.assertIn("Otwórz miejsce w WreckScanner", report_html)
                self.assertIn('class="report-inline-link"', report_html)
                self.assertIn("https://wreckscanner.pl/?lat=51.100000&amp;lon=17.200000", report_html)
                self.assertIn("Typ terenu: B - tereny mieszkaniowe", report_html)
                self.assertNotIn("Powierzchnia:", report_html)
                self.assertNotIn("Kontur:", report_html)
                self.assertNotIn("identifyParcel", report_html)

    def test_create_field_photo_report_package_requires_approved_vehicle_photos(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir, photo_id = create_field_photo_fixture(root, status="pending")

            with self.assertRaisesRegex(ValueError, "zatwierdzonych"):
                create_field_photo_report_package(
                    valid_fields(), [photo_id], lat=51.1, lon=17.2, field_photos_dir=field_dir
                )

            field_dir, photo_id = create_field_photo_fixture(root, issue_type="smoke")
            with self.assertRaisesRegex(ValueError, "pojazdów"):
                create_field_photo_report_package(
                    valid_fields(), [photo_id], lat=51.1, lon=17.2, field_photos_dir=field_dir
                )

    def test_report_pdf_starts_with_formal_letter_before_evidence(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            pdf_bytes = report_pdf.build_report_pdf(
                record={
                    "id": "field_photo_group_test",
                    "status": "field_photo_group",
                    "lat": 51.1,
                    "lon": 17.2,
                    "labels_present": ["2024", "2025"],
                    "first_seen_year": 2024,
                    "last_seen_year": 2025,
                    "links": {},
                    "attached_photos": [],
                },
                evidence={
                    "id": "report_test",
                    "labels_present": ["2024", "2025"],
                    "path": "evidence/report_test",
                    "crops": [],
                    "links": {},
                },
                record_dir=record_dir,
                evidence_base_dir=record_dir,
                recipient="interwencje@example.test",
                subject="Zgłoszenie",
                mail_body="Treść zgłoszenia",
            )

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()

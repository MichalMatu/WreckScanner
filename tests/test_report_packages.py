import base64
import io
import json
import shutil
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

import core.report_pdf as report_pdf
from app.http.public import reject_report_package_files
from core import config as core_config
from core.report_assets import report_package_download_name
from core.report_models import validate_report_fields
from core.report_packages import (
    create_public_report_package,
    create_report_package,
)
from core.uploads import UploadedFile
from core.wrecks_save import save_vehicle_case


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


def fake_save_location_crops(lat: float, lon: float, output_dir: Path, **_kwargs):
    output_dir.mkdir(parents=True, exist_ok=True)
    for year in (2024, 2025):
        (output_dir / f"{year}.jpg").write_bytes(image_bytes())
    return (
        [{"label": "2024", "file": "2024.jpg"}, {"label": "2025", "file": "2025.jpg"}],
        {
            "center_lat": lat,
            "center_lon": lon,
            "crop_meters": 7.5,
            "years": [2024, 2025],
            "source": "wroclaw_wms_location_crops",
        },
    )


def create_wreck_fixture(root: Path) -> Path:
    wrecks_dir = root / "zidentyfikowane_wraki"
    record_dir = wrecks_dir / "wreck_51100000_17200000"
    evidence_dir = record_dir / "evidence" / "abc123"
    attached_photo_dir = record_dir / "photos" / "photo_20260603T000000Z_abcdef12"
    evidence_dir.mkdir(parents=True)
    attached_photo_dir.mkdir(parents=True)
    (evidence_dir / "2025.jpg").write_bytes(image_bytes())
    (attached_photo_dir / "original.jpg").write_bytes(image_bytes())
    (attached_photo_dir / "thumb.jpg").write_bytes(image_bytes())
    (attached_photo_dir / "public.jpg").write_bytes(image_bytes())
    (attached_photo_dir / "public_thumb.jpg").write_bytes(image_bytes())
    (record_dir / "index.html").write_text(
        '<html><body><img src="evidence/abc123/2025.jpg"></body></html>',
        encoding="utf-8",
    )
    write_json(attached_photo_dir / "record.json", {"id": "photo_20260603T000000Z_abcdef12"})
    write_json(
        record_dir / "record.json",
        {
            "id": "wreck_51100000_17200000",
            "status": "confirmed",
            "lat": 51.1,
            "lon": 17.2,
            "labels_present": ["2025"],
            "latest_evidence": {
                "id": "abc123",
                "path": "evidence/abc123",
                "labels_present": ["2025"],
                "crops": [{"label": "2025", "file": "2025.jpg"}],
                "links": {"geoportal": "https://example.test/geo"},
            },
            "links": {
                "street_view": "https://example.test/street",
                "geoportal": "https://example.test/geo",
            },
            "attached_photos": [
                {
                    "id": "photo_20260603T000000Z_abcdef12",
                    "created_at": "2026-06-03T00:00:00Z",
                    "original_filename": "teren.jpg",
                    "original_file": "photos/photo_20260603T000000Z_abcdef12/original.jpg",
                    "thumb_file": "photos/photo_20260603T000000Z_abcdef12/thumb.jpg",
                    "public_image_file": "photos/photo_20260603T000000Z_abcdef12/public.jpg",
                    "public_thumb_file": "photos/photo_20260603T000000Z_abcdef12/public_thumb.jpg",
                    "public_review_status": "approved",
                    "redactions": [],
                    "reviewed_at": "2026-06-03T00:00:00Z",
                }
            ],
            "evidences": [],
        },
    )
    return wrecks_dir


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

    def test_report_package_rejects_direct_photo_files(self):
        with self.assertRaisesRegex(ValueError, "zanonimizuj"):
            reject_report_package_files([UploadedFile("photos[]", "teren.jpg", "image/jpeg", image_bytes())])

    def test_create_report_package_generates_zip_and_keeps_record_without_reporter_data(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrecks_dir = create_wreck_fixture(root)
            public_index_path = wrecks_dir / "wreck_51100000_17200000" / "index.html"
            record_path = wrecks_dir / "wreck_51100000_17200000" / "record.json"
            record_dir = wrecks_dir / "wreck_51100000_17200000"
            original_record_text = record_path.read_text(encoding="utf-8")
            original_index_text = public_index_path.read_text(encoding="utf-8")
            original_evidence_paths = sorted(
                path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
            )

            with patch("core.wrecks_evidence.save_location_crops", side_effect=fake_save_location_crops):
                result = create_report_package(
                    "wreck_51100000_17200000",
                    valid_fields(),
                    wrecks_dir,
                )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["recipient"], "interwencje@smwroclaw.pl")
            self.assertIn("Zgłoszenie pojazdu nieużytkowanego", result["subject"])
            self.assertIn("Jan Kowalski", result["body"])
            self.assertEqual(result["zip_filename"], report_package_download_name(result["package_id"], "zip"))
            self.assertEqual(result["pdf_filename"], report_package_download_name(result["package_id"], "pdf"))
            self.assertNotIn("zip_url", result)
            self.assertNotIn("pdf_url", result)
            self.assertIn("zip_base64", result)
            self.assertIn("pdf_base64", result)
            self.assertEqual(record_path.read_text(encoding="utf-8"), original_record_text)
            self.assertEqual(public_index_path.read_text(encoding="utf-8"), original_index_text)
            current_evidence_paths = sorted(
                path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
            )
            self.assertEqual(current_evidence_paths, original_evidence_paths)

            zip_bytes = base64.b64decode(result["zip_base64"])
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
                names = set(archive.namelist())
                self.assertIn("zgloszenie.txt", names)
                self.assertIn("raport.html", names)
                self.assertIn("miniatury_historyczne/2024.jpg", names)
                self.assertIn("miniatury_historyczne/2025.jpg", names)
                self.assertIn("photos/photo_20260603T000000Z_abcdef12/public_thumb.jpg", names)
                self.assertIn("photos/photo_20260603T000000Z_abcdef12/public.jpg", names)
                self.assertFalse(any(name.startswith("zdjecia_z_miejsca/") for name in names))
                self.assertNotIn("photos/photo_20260603T000000Z_abcdef12/original.jpg", names)
                self.assertNotIn("metadane/record.json", names)
                self.assertFalse(any(name.startswith("evidence/") for name in names))
                self.assertEqual(archive.read("miniatury_historyczne/2024.jpg"), image_bytes())
                self.assertEqual(archive.read("miniatury_historyczne/2025.jpg"), image_bytes())
                draft_text = archive.read("zgloszenie.txt").decode("utf-8")
                self.assertIn("Jan Kowalski", draft_text)
                self.assertIn("Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne", draft_text)
                self.assertNotIn("pakiet dowodowy ZIP", draft_text)
                self.assertNotIn("W załączniku", draft_text)
                self.assertNotIn("Linki do weryfikacji", draft_text)
                self.assertNotIn("Street View", draft_text)
                self.assertNotIn("https://example.test/street", draft_text)
                report_html = archive.read("raport.html").decode("utf-8")
                self.assertIn("Zgłoszenie dotyczące pojazdu nieużytkowanego", report_html)
                self.assertIn("Data zgłoszenia:", report_html)
                self.assertIn("interwencje@smwroclaw.pl", report_html)
                self.assertIn("<strong>Dotyczy:</strong>", report_html)
                self.assertIn(result["subject"], report_html)
                self.assertIn("Dane osoby zgłaszającej", report_html)
                self.assertIn("Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne", report_html)
                self.assertIn("Jan Kowalski", report_html)
                self.assertIn("Zdjęcia z miejsca", report_html)
                self.assertIn("Miniatury historyczne", report_html)
                self.assertIn("photos/photo_20260603T000000Z_abcdef12/public.jpg", report_html)
                self.assertNotIn("photos/photo_20260603T000000Z_abcdef12/original.jpg", report_html)
                self.assertNotIn("Historia działań", report_html)
                self.assertNotIn("report_20260601T100000Z_deadbeef", report_html)
                self.assertNotIn("lokalna sprawa", report_html)
                self.assertNotIn("Zdjęcia dołączone do zgłoszenia", report_html)
                self.assertNotIn("zdjecia_z_miejsca", report_html)
                self.assertIn("data-report-package-style", report_html)
                self.assertLess(report_html.index("Dane osoby zgłaszającej"), report_html.index("Zdjęcia z miejsca"))
                self.assertLess(report_html.index("Zdjęcia z miejsca"), report_html.index("Miniatury historyczne"))
                self.assertNotIn("Teczka pojazdu", report_html)
                self.assertNotIn("Współrzędne:", report_html)
                self.assertNotIn("data-report-photo-upload", report_html)
                self.assertNotIn("Linki do weryfikacji", report_html)
                self.assertNotIn("Street View", report_html)
                self.assertNotIn("https://example.test/street", report_html)
                self.assertNotIn("pakiet dowodowy ZIP", report_html)
                self.assertNotIn("W załączniku", report_html)

            pdf_bytes = base64.b64decode(result["pdf_base64"])
            self.assertGreater(len(pdf_bytes), 10_000)
            self.assertEqual(pdf_bytes[:5], b"%PDF-")
            self.assertEqual(result["zip_size_bytes"], len(zip_bytes))
            self.assertGreater(result["pdf_size_bytes"], 10_000)

    def test_create_report_package_generates_map_crops_for_photo_ready_case(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrecks_dir = root / "zidentyfikowane_wraki"
            saved = save_vehicle_case(51.088784, 17.035782, wrecks_dir, dedupe_existing=True)
            wreck_id = saved["wreck"]["id"]
            record_dir = wrecks_dir / wreck_id
            record_path = record_dir / "record.json"
            original_record_text = record_path.read_text(encoding="utf-8")
            original_evidence_paths = sorted(
                path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
            )

            with patch("core.wrecks_evidence.save_location_crops", side_effect=fake_save_location_crops):
                result = create_report_package(wreck_id, valid_fields(), wrecks_dir)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["zip_filename"], report_package_download_name(result["package_id"], "zip"))
            self.assertNotIn("zip_url", result)
            self.assertEqual(record_path.read_text(encoding="utf-8"), original_record_text)
            current_evidence_paths = sorted(
                path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
            )
            self.assertEqual(current_evidence_paths, original_evidence_paths)
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["zip_base64"]))) as archive:
                names = set(archive.namelist())
                self.assertIn("zgloszenie.txt", names)
                self.assertIn("raport.html", names)
                self.assertNotIn("metadane/record.json", names)
                self.assertIn("miniatury_historyczne/2024.jpg", names)
                self.assertIn("miniatury_historyczne/2025.jpg", names)
                self.assertFalse(any(name.endswith(".json") for name in names))
                draft_text = archive.read("zgloszenie.txt").decode("utf-8")
                report_html = archive.read("raport.html").decode("utf-8")
                self.assertIn("Zgłoszenie dotyczące pojazdu nieużytkowanego", report_html)
                self.assertIn("Miniatury historyczne", report_html)
                self.assertLess(
                    report_html.index("Dane osoby zgłaszającej"), report_html.index("Miniatury historyczne")
                )
                self.assertNotIn("Teczka pojazdu", report_html)
                self.assertNotIn("Współrzędne:", report_html)
                self.assertNotIn("Linki do weryfikacji", draft_text)
                self.assertNotIn("pakiet dowodowy ZIP", draft_text)
                self.assertNotIn("Linki do weryfikacji", report_html)
                self.assertNotIn("pakiet dowodowy ZIP", report_html)
            self.assertEqual(base64.b64decode(result["pdf_base64"])[:5], b"%PDF-")

    def test_create_public_report_package_uses_clean_assets_and_token(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrecks_dir = create_wreck_fixture(root)
            record_path = wrecks_dir / "wreck_51100000_17200000" / "record.json"
            record_dir = wrecks_dir / "wreck_51100000_17200000"

            with patch("core.wrecks_evidence.save_location_crops", side_effect=fake_save_location_crops):
                original_record_text = record_path.read_text(encoding="utf-8")
                original_evidence_paths = sorted(
                    path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
                )
                result = create_public_report_package(
                    "wreck_51100000_17200000",
                    valid_fields(),
                    wrecks_dir,
                )

                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["zip_filename"], report_package_download_name(result["package_id"], "zip"))
                self.assertEqual(result["pdf_filename"], report_package_download_name(result["package_id"], "pdf"))
                self.assertNotIn("zip_url", result)
                self.assertNotIn("pdf_url", result)
                self.assertNotIn("expires_at", result)

            self.assertEqual(record_path.read_text(encoding="utf-8"), original_record_text)
            current_evidence_paths = sorted(
                path.relative_to(record_dir).as_posix() for path in (record_dir / "evidence").rglob("*")
            )
            self.assertEqual(current_evidence_paths, original_evidence_paths)
            with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["zip_base64"]))) as archive:
                names = set(archive.namelist())
                self.assertIn("zgloszenie.txt", names)
                self.assertIn("raport.html", names)
                self.assertIn("miniatury_historyczne/2024.jpg", names)
                self.assertIn("miniatury_historyczne/2025.jpg", names)
                self.assertIn("photos/photo_20260603T000000Z_abcdef12/public_thumb.jpg", names)
                self.assertIn("photos/photo_20260603T000000Z_abcdef12/public.jpg", names)
                self.assertFalse(any(name.startswith("zdjecia_z_miejsca/") for name in names))
                self.assertNotIn("metadane/record.json", names)
                self.assertFalse(any(name.startswith("evidence/") for name in names))
                self.assertNotIn("photos/photo_20260603T000000Z_abcdef12/original.jpg", names)
                draft_text = archive.read("zgloszenie.txt").decode("utf-8")
                report_html = archive.read("raport.html").decode("utf-8")
                self.assertIn("Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne", draft_text)
                self.assertNotIn("pakiet dowodowy ZIP", draft_text)
                self.assertNotIn("Linki do weryfikacji", draft_text)
                self.assertNotIn("Street View", draft_text)
                self.assertNotIn("https://example.test/street", draft_text)
                self.assertIn("Zgłoszenie dotyczące pojazdu nieużytkowanego", report_html)
                self.assertIn("Zdjęcia z miejsca", report_html)
                self.assertIn("Miniatury historyczne", report_html)
                self.assertLess(report_html.index("Dane osoby zgłaszającej"), report_html.index("Zdjęcia z miejsca"))
                self.assertLess(report_html.index("Zdjęcia z miejsca"), report_html.index("Miniatury historyczne"))
                self.assertNotIn("Teczka pojazdu", report_html)
                self.assertNotIn("Współrzędne:", report_html)
                self.assertNotIn("Linki do weryfikacji", report_html)
                self.assertNotIn("Street View", report_html)
                self.assertNotIn("https://example.test/street", report_html)
                self.assertNotIn("pakiet dowodowy ZIP", report_html)

    def test_report_pdf_starts_with_formal_letter_before_evidence(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            pdf_bytes = report_pdf.build_report_pdf(
                record={
                    "id": "wreck_51100000_17200000",
                    "status": "confirmed",
                    "lat": 51.1,
                    "lon": 17.2,
                    "labels_present": ["2024", "2025"],
                    "links": {},
                    "evidences": [],
                },
                evidence={"path": "", "crops": [], "created_at": "2026-07-02T14:30:31Z"},
                record_dir=record_dir,
                evidence_base_dir=record_dir,
                recipient=core_config.REPORT_RECIPIENT,
                subject="Zgłoszenie pojazdu nieużytkowanego - ul. Długa 10",
                mail_body="Dzień dobry,\n\nZakres oczekiwanej odpowiedzi:\nWnoszę o odpowiedź.",
            )
            pdf_path = record_dir / "report.pdf"
            pdf_path.write_bytes(pdf_bytes)

            self.assertEqual(pdf_bytes[:5], b"%PDF-")
            self.assertIn(b"mailto:interwencje@smwroclaw.pl", pdf_bytes)
            self.assertIn(b"/Subtype /Link", pdf_bytes)
            self.assertIn(b"/Subtype /TrueType", pdf_bytes)
            if shutil.which("pdftotext"):
                text = subprocess.check_output(["pdftotext", str(pdf_path), "-"], text=True)
                normalized_text = " ".join(text.split())
                self.assertIn("Zgłoszenie dotyczące pojazdu nieużytkowanego", normalized_text)
                self.assertIn("Data zgłoszenia: 02.07.2026, godz.", text)
                self.assertIn("Straż Miejska Wrocławia", text)
                self.assertIn("interwencje@smwroclaw.pl", text)
                self.assertIn("Dotyczy: Zgłoszenie pojazdu nieużytkowanego - ul. Długa 10", text)
                self.assertIn("Zakres oczekiwanej odpowiedzi", text)
                self.assertNotIn("Historia działań", text)
                self.assertNotIn("lokalna sprawa", text)
                self.assertNotIn("Zdjęcia dołączone do zgłoszenia", text)
                self.assertNotIn("Teczka pojazdu wreck_51100000_17200000", normalized_text)
                self.assertNotIn("Linki do weryfikacji", text)
                self.assertNotIn("Treść zgłoszenia", text)
                self.assertNotIn("pakiet dowodowy ZIP", text)

    def test_report_pdf_does_not_force_evidence_onto_a_new_page_after_short_text_overflow(self):
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext is not installed")

        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            photo_dir = record_dir / "photos" / "photo_20260603T000000Z_abcdef12"
            evidence_dir = record_dir / "evidence" / "report_test"
            photo_dir.mkdir(parents=True)
            evidence_dir.mkdir(parents=True)
            (photo_dir / "public.jpg").write_bytes(image_bytes())
            (photo_dir / "public_thumb.jpg").write_bytes(image_bytes())
            (evidence_dir / "2025.jpg").write_bytes(image_bytes())

            record = {
                "id": "wreck_51100000_17200000",
                "status": "confirmed",
                "lat": 51.1,
                "lon": 17.2,
                "attached_photos": [
                    {
                        "id": "photo_20260603T000000Z_abcdef12",
                        "original_filename": "teren.jpg",
                        "public_review_status": "approved",
                        "public_image_file": "photos/photo_20260603T000000Z_abcdef12/public.jpg",
                        "public_thumb_file": "photos/photo_20260603T000000Z_abcdef12/public_thumb.jpg",
                    }
                ],
            }
            evidence = {
                "path": "evidence/report_test",
                "crops": [{"label": "2025", "file": "2025.jpg"}],
                "created_at": "2026-07-02T14:30:31Z",
            }
            base = (
                "Dzień dobry,\n\nZgłaszam pojazd, który od dłuższego czasu wygląda na nieużytkowany.\n\nOpis miejsca:\n"
            )
            sentence = (
                "Pojazd stoi na ogólnodostępnym miejscu postojowym, nie zmienia położenia mimo rotacji "
                "innych samochodów, a jego stan wskazuje na brak bieżącej eksploatacji. "
            )
            closing = (
                "\n\nZakres oczekiwanej odpowiedzi:\n"
                "Wnoszę o weryfikację przez patrol, wskazanie numeru sprawy oraz pisemną informację "
                "o podjętych czynnościach.\n\n"
                "Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne dołączone "
                "do niniejszego zgłoszenia.\n\n"
                "Z poważaniem,\nJan Kowalski"
            )

            for repetitions in (4, 8, 12, 16):
                pdf_bytes = report_pdf.build_report_pdf(
                    record=record,
                    evidence=evidence,
                    record_dir=record_dir,
                    evidence_base_dir=record_dir,
                    recipient=core_config.REPORT_RECIPIENT,
                    subject="Zgłoszenie pojazdu nieużytkowanego - ul. Testowa",
                    mail_body=base + (sentence * repetitions) + closing,
                )
                pdf_path = record_dir / f"layout_{repetitions}.pdf"
                pdf_path.write_bytes(pdf_bytes)
                text = subprocess.check_output(["pdftotext", str(pdf_path), "-"], text=True)
                pages = [page for page in text.split("\f") if page.strip()]
                signature_pages = [page for page in pages if "Z poważaniem" in page]
                self.assertEqual(len(signature_pages), 1)
                signature_page = signature_pages[0]
                non_empty_lines = [line for line in signature_page.splitlines() if line.strip()]
                has_evidence = "Zdjęcia z miejsca" in signature_page or "Miniatury historyczne" in signature_page
                self.assertTrue(
                    len(non_empty_lines) > 8 or has_evidence,
                    f"orphaned signature page for {repetitions} repetitions:\n{signature_page}",
                )

    def test_report_pdf_uses_approved_public_attached_photo(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            photo_dir = record_dir / "photos" / "photo_20260603T000000Z_abcdef12"
            photo_dir.mkdir(parents=True)
            public = image_bytes()
            thumb = b"tiny-thumbnail"
            (photo_dir / "public.jpg").write_bytes(public)
            (photo_dir / "public_thumb.jpg").write_bytes(thumb)

            photo = report_pdf._photo_bytes_from_record(
                record_dir,
                {
                    "id": "photo_20260603T000000Z_abcdef12",
                    "original_filename": "teren.jpg",
                    "public_review_status": "approved",
                    "public_image_file": "photos/photo_20260603T000000Z_abcdef12/public.jpg",
                    "public_thumb_file": "photos/photo_20260603T000000Z_abcdef12/public_thumb.jpg",
                },
            )

            self.assertIsNotNone(photo)
            self.assertEqual(photo.data, public)

            pending = report_pdf._photo_bytes_from_record(
                record_dir,
                {
                    "id": "photo_20260603T000000Z_abcdef12",
                    "public_review_status": "pending",
                    "public_image_file": "photos/photo_20260603T000000Z_abcdef12/public.jpg",
                },
            )
            self.assertIsNone(pending)


if __name__ == "__main__":
    unittest.main()

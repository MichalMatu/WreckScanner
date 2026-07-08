import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from core.data_diagnostics import format_data_diagnostics, run_data_diagnostics
from core.field_photos import load_field_photo_record, save_field_photo_record

ROOT_DIR = Path(__file__).resolve().parent.parent


def write_image(path: Path, size: tuple[int, int] = (48, 32)) -> None:
    out = io.BytesIO()
    Image.new("RGB", size, (80, 120, 160)).save(out, "JPEG")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.getvalue())


def write_field_photo_record(
    field_dir: Path,
    private_dir: Path,
    photo_id: str = "photo_20260604T200730Z_37885295",
    *,
    issue_type: str | None = "vehicle",
    private_original_file: str | None = None,
    public_review_status: str = "approved",
    public_image_file: str | None = "public.jpg",
    public_thumb_file: str | None = "public_thumb.jpg",
    image_size: tuple[int, int] = (48, 32),
    thumb_size: tuple[int, int] = (36, 24),
    write_private: bool = True,
    write_public: bool = True,
) -> Path:
    record_dir = field_dir / photo_id
    private_original = private_original_file or f"field_photos/{photo_id}/original.jpg"
    if write_private and not private_original.startswith("../") and "\\" not in private_original:
        write_image(private_dir / private_original, image_size)
    if write_public and public_review_status == "approved" and public_image_file and "../" not in public_image_file:
        write_image(record_dir / public_image_file, image_size)
    if write_public and public_review_status == "approved" and public_thumb_file and "../" not in public_thumb_file:
        write_image(record_dir / public_thumb_file, thumb_size)
    record = {
        "id": photo_id,
        "created_at": "2026-06-04T20:07:30Z",
        "original_filename": "teren.jpg",
        "content_type": "image/jpeg",
        "format": "JPEG",
        "size_bytes": 123,
        "image_width": image_size[0],
        "image_height": image_size[1],
        "lat": 51.1,
        "lon": 17.2,
        "coordinate_source": "map",
        "private_original_file": private_original,
        "public_review_status": public_review_status,
        "redactions": [],
        "reviewed_at": "2026-06-04T20:08:00Z" if public_review_status == "approved" else None,
    }
    if public_image_file:
        record["public_image_file"] = public_image_file
    if public_thumb_file:
        record["public_thumb_file"] = public_thumb_file
    if issue_type is not None:
        record["issue_type"] = issue_type
    save_field_photo_record(record, field_dir)
    return record_dir


class DataDiagnosticsTests(unittest.TestCase):
    def test_run_data_diagnostics_reports_healthy_field_photos(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"

            write_field_photo_record(field_dir, private_dir, issue_type="vehicle")
            write_field_photo_record(
                field_dir,
                private_dir,
                "photo_20260604T200810Z_6b21b28a",
                issue_type="smoke",
                image_size=(50, 40),
                thumb_size=(36, 28),
            )

            report = run_data_diagnostics(field_photos_dir=field_dir, private_photos_dir=private_dir)

            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["summary"]["field_photos"]["records"], 2)
            self.assertEqual(report["summary"]["field_photos"]["issue_types"]["vehicle"], 1)
            self.assertEqual(report["summary"]["field_photos"]["issue_types"]["smoke"], 1)
            self.assertEqual(report["summary"]["field_photos"]["vehicle_resolution_statuses"]["active"], 1)
            self.assertNotIn("wrecks_dir", report["roots"])
            self.assertIn("Zdjęcia terenowe: 2 rekordów", format_data_diagnostics(report))
            self.assertNotIn("Sprawy pojazdów", format_data_diagnostics(report))

    def test_run_data_diagnostics_blocks_legacy_report_packages(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            legacy_report_dir = root / "prywatne_zgloszenia" / "wreck_51000000_17000000"
            legacy_report_dir.mkdir(parents=True)
            (legacy_report_dir / "report_20260702T120000Z_deadbeef.zip").write_bytes(b"zip")
            (legacy_report_dir / "report_20260702T120000Z_deadbeef.pdf").write_bytes(b"pdf")

            write_field_photo_record(field_dir, private_dir)

            report = run_data_diagnostics(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                check_images=False,
            )

            codes = {issue["code"] for issue in report["issues"]}
            self.assertEqual(report["status"], "error")
            self.assertIn("legacy_report_packages_present", codes)
            self.assertEqual(report["summary"]["legacy_report_packages"]["files"], 2)
            self.assertEqual(report["summary"]["legacy_report_packages"]["directories"], 1)
            self.assertIn("Stare pakiety raportów: 1 katalogów, 2 plików", format_data_diagnostics(report))

    def test_run_data_diagnostics_finds_missing_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"

            write_field_photo_record(
                field_dir,
                private_dir,
                private_original_file="field_photos/photo_20260604T200730Z_37885295/missing.jpg",
                write_private=False,
                write_public=False,
            )

            report = run_data_diagnostics(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                check_images=False,
            )

            self.assertEqual(report["status"], "error")
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("field_photo_private_original_missing", codes)
            self.assertIn("field_photo_public_image_missing_file", codes)
            self.assertIn("field_photo_public_thumb_missing_file", codes)

    def test_run_data_diagnostics_finds_unsafe_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"

            write_field_photo_record(field_dir, private_dir, private_original_file="../outside.jpg")

            report = run_data_diagnostics(
                field_photos_dir=field_dir,
                private_photos_dir=private_dir,
                check_images=False,
            )

            codes = {issue["code"] for issue in report["issues"]}
            self.assertEqual(report["status"], "error")
            self.assertIn("field_photo_unsafe_private_original_path", codes)

    def test_run_data_diagnostics_finds_unreadable_images_size_mismatch_and_large_thumbnail(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"

            record_dir = write_field_photo_record(field_dir, private_dir, image_size=(48, 32), thumb_size=(480, 320))
            private_original = private_dir / f"field_photos/{record_dir.name}/original.jpg"
            private_original.write_bytes(b"not an image")
            record = load_field_photo_record(record_dir.name, field_dir, private_dir=private_dir)
            record["image_width"] = 64
            record["image_height"] = 64
            save_field_photo_record(record, field_dir)
            mismatch_dir = write_field_photo_record(
                field_dir,
                private_dir,
                "photo_20260604T200810Z_6b21b28a",
                image_size=(50, 40),
                thumb_size=(36, 28),
            )
            mismatch_record = load_field_photo_record(mismatch_dir.name, field_dir, private_dir=private_dir)
            mismatch_record["image_width"] = 99
            mismatch_record["image_height"] = 88
            save_field_photo_record(mismatch_record, field_dir)

            report = run_data_diagnostics(field_photos_dir=field_dir, private_photos_dir=private_dir)

            codes = {issue["code"] for issue in report["issues"]}
            self.assertEqual(report["status"], "error")
            self.assertIn("image_unreadable", codes)
            self.assertIn("field_photo_public_thumb_too_large", codes)
            self.assertIn("field_photo_size_mismatch", codes)

    def test_diagnose_data_cli_outputs_json_without_archived_case_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_dir = root / "zdjecia_terenowe"
            private_dir = root / "prywatne_zdjecia"
            write_field_photo_record(field_dir, private_dir)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "diagnose_data.py"),
                    "--field-photos-dir",
                    str(field_dir),
                    "--private-photos-dir",
                    str(private_dir),
                    "--no-image-check",
                    "--json",
                ],
                cwd=ROOT_DIR,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertNotIn("wrecks_dir", payload["roots"])


if __name__ == "__main__":
    unittest.main()

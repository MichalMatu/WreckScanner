import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PIL import Image

from core import config as core_config
from core.field_photos import list_field_photos, save_field_photo
from core.uploads import UploadedFile
from core.wrecks import delete_wreck, list_wrecks, review_wreck
from core.wrecks_assets import public_wreck_asset, wreck_is_public, wreck_photo_original_asset
from core.wrecks_attachments import attach_field_photos_to_wreck, attach_wreck_photos, review_wreck_photo
from core.wrecks_catalog import find_existing_record, load_records
from core.wrecks_evidence import first_last_year
from core.wrecks_identity import validate_coordinates, wreck_id
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_photos import attached_photo_by_id, save_attached_photo
from core.wrecks_public import wreck_public_file_url, wreck_summary
from core.wrecks_rendering import approved_attached_photos, render_record_html
from core.wrecks_review import apply_wreck_photo_review, apply_wreck_review, wreck_photo_review_item, wreck_review_items
from core.wrecks_save import save_vehicle_case
from core.wrecks_store import record_dir_for, validate_wreck_id


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def image_bytes() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (32, 24), (80, 110, 140)).save(out, "JPEG")
    return out.getvalue()


def upload(data: bytes, filename: str = "miejsce.jpg") -> UploadedFile:
    return UploadedFile(field_name="photos[]", filename=filename, content_type="image/jpeg", data=data)


def field_upload(data: bytes, filename: str = "teren.jpg") -> UploadedFile:
    return UploadedFile(field_name="photo", filename=filename, content_type="image/jpeg", data=data)


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


class WreckIdentityCatalogTests(unittest.TestCase):
    def test_identity_helpers_validate_coordinates_and_stable_id(self):
        self.assertEqual(validate_coordinates("51.1", "17.2"), (51.1, 17.2))
        self.assertEqual(wreck_id(51.1, 17.2), "wreck_51100000_17200000")

        with self.assertRaisesRegex(ValueError, "współrzędne"):
            validate_coordinates("nan", "17.2")

        with self.assertRaisesRegex(ValueError, "poza dozwolonym"):
            validate_coordinates("91", "17.2")

    def test_catalog_loads_migrates_and_finds_nearest_record(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp)
            write_json(
                wrecks_dir / "wreck_51100000_17200000" / "record.json",
                {
                    "id": "wreck_51100000_17200000",
                    "lat": 51.1,
                    "lon": 17.2,
                    "created_at": "2026-06-01T00:00:00Z",
                    "labels_present": [],
                    "evidences": [],
                },
            )
            write_json(
                wrecks_dir / "wreck_51101000_17201000" / "record.json",
                {
                    "id": "wreck_51101000_17201000",
                    "lat": 51.101,
                    "lon": 17.201,
                    "public_review_status": "approved",
                    "labels_present": [],
                    "evidences": [],
                },
            )
            write_json(wrecks_dir / "bad" / "record.json", ["not", "a", "record"])

            records = load_records(wrecks_dir)
            existing, distance_m = find_existing_record(wrecks_dir, 51.100001, 17.200001)

            self.assertEqual(
                [record["id"] for record in records], ["wreck_51100000_17200000", "wreck_51101000_17201000"]
            )
            migrated = json.loads((wrecks_dir / "wreck_51100000_17200000" / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(migrated["public_review_status"], "approved")
            self.assertEqual(migrated["submission_owner"], None)
            self.assertEqual(existing["id"], "wreck_51100000_17200000")
            self.assertIsNotNone(distance_m)


class VehicleCaseContractTests(unittest.TestCase):
    def test_save_vehicle_case_creates_photo_ready_record_and_dedupes_nearby_location(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp) / "wraki"

            first = save_vehicle_case(51.088784, 17.035782, wrecks_dir)
            second = save_vehicle_case(51.088785, 17.035783, wrecks_dir)

            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(len(list_wrecks(wrecks_dir)), 0)

            record_path = next(wrecks_dir.glob("*/record.json"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "field_photo_case")
            self.assertEqual(record["source"], "field_photo")
            self.assertEqual(record["labels_present"], [])
            self.assertEqual(record["evidences"], [])
            self.assertNotIn("latest_evidence", record)
            self.assertNotIn("best_score", record)
            self.assertTrue((record_path.parent / "index.html").exists())

    def test_save_vehicle_case_uses_location_without_previous_area_state(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp) / "wraki"

            result = save_vehicle_case(51.2, 17.2, wrecks_dir)

            self.assertEqual(result["status"], "ok")
            self.assertTrue((wrecks_dir / result["wreck"]["id"] / "record.json").exists())

    def test_photo_less_vehicle_case_is_hidden_from_map_lists_even_after_review(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp) / "wraki"

            result = save_vehicle_case(
                51.088784,
                17.035782,
                wrecks_dir,
                public_review_status="pending",
                submission_owner="public:test",
            )

            self.assertEqual(list_wrecks(wrecks_dir), [])
            admin_wrecks = list_wrecks(wrecks_dir, include_pending=True)
            self.assertEqual(admin_wrecks, [])

            review_wreck(result["wreck"]["id"], wrecks_dir, status="approved")

            public_wrecks = list_wrecks(wrecks_dir)
            self.assertEqual(public_wrecks, [])

    def test_vehicle_case_dedupe_approval_is_persisted(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp) / "wraki"

            first = save_vehicle_case(
                51.088784,
                17.035782,
                wrecks_dir,
                public_review_status="pending",
            )
            second = save_vehicle_case(51.088785, 17.035783, wrecks_dir)

            self.assertFalse(second["created"])
            record = json.loads((wrecks_dir / first["wreck"]["id"] / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(record["public_review_status"], "approved")
            self.assertIsNotNone(record["reviewed_at"])

    def test_save_vehicle_case_rejects_invalid_coordinates(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp) / "wraki"

            with self.assertRaises(ValueError):
                save_vehicle_case("not-a-lat", 17.035782, wrecks_dir)
            with self.assertRaises(ValueError):
                save_vehicle_case(91, 17.035782, wrecks_dir)

    def test_evidence_year_range_helper_uses_numeric_labels(self):
        self.assertEqual(first_last_year(["x", "2025", "2024"]), (2024, 2025))
        self.assertEqual(first_last_year(["x"]), (None, None))


class WreckPhotosRenderingTests(unittest.TestCase):
    def test_attach_field_photos_to_wreck_marks_source_and_hides_loose_pin(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            field_photos_dir = root / "zdjecia_terenowe"
            wrecks_dir = root / "zidentyfikowane_wraki"
            private_dir = root / "prywatne_zdjecia"

            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                field_result = save_field_photo(
                    field_upload(image_bytes()),
                    field_photos_dir,
                    map_lat=51.1,
                    map_lon=17.2,
                    public_review_status="approved",
                )
                photo_id = field_result["photo"]["id"]
                case = save_vehicle_case(51.1, 17.2, wrecks_dir)
                result = attach_field_photos_to_wreck(case["wreck"]["id"], [photo_id], field_photos_dir, wrecks_dir)

                self.assertEqual(result["attached_count"], 1)
                self.assertEqual(result["copied_field_photo_ids"], [photo_id])
                field_record_path = field_photos_dir / photo_id / "record.json"
                self.assertTrue(field_record_path.exists())
                field_record = json.loads(field_record_path.read_text(encoding="utf-8"))
                self.assertEqual(field_record["attached_wreck_id"], case["wreck"]["id"])
                self.assertTrue(field_record["attached_at"])
                self.assertTrue((private_dir / "field_photos" / photo_id / "original.jpg").exists())
                self.assertTrue(
                    (private_dir / "wreck_photos" / case["wreck"]["id"] / photo_id / "original.jpg").exists()
                )
                self.assertEqual(list_field_photos(field_photos_dir), [])
                summary = list_wrecks(wrecks_dir)[0]

            self.assertEqual(summary["photo_count"], 1)
            self.assertEqual(summary["field_photo_previews"][0]["source"], "attached")

    def test_attach_wreck_photos_updates_record_files_and_public_report(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp)
            record_dir = wrecks_dir / "wreck_51100000_17200000"
            write_json(
                record_dir / "record.json",
                {
                    "id": "wreck_51100000_17200000",
                    "status": "confirmed",
                    "lat": 51.1,
                    "lon": 17.2,
                    "labels_present": ["2020", "2021", "2022", "2023", "2024", "2025"],
                    "latest_evidence": {"created_at": "2026-05-29T11:11:53Z"},
                    "links": {"geoportal": "https://example.test/geo"},
                    "evidences": [],
                },
            )

            private_dir = Path(tmp) / "private"
            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                result = attach_wreck_photos("wreck_51100000_17200000", [upload(image_bytes())], wrecks_dir)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["photo_count"], 1)
            record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
            photo = record["attached_photos"][0]
            self.assertEqual(photo["public_review_status"], "pending")
            self.assertTrue((private_dir / photo["private_original_file"]).exists())
            self.assertNotIn("original_file", photo)
            self.assertNotIn("thumb_file", photo)
            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                self.assertEqual(list_wrecks(wrecks_dir), [])
                summary = list_wrecks(wrecks_dir, include_pending=True)[0]
            self.assertEqual(summary["photo_count"], 0)
            self.assertEqual(summary["review_photo_count"], 1)
            self.assertEqual(summary["field_photo_previews"], [])

            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                review_wreck_photo(
                    "wreck_51100000_17200000",
                    photo["id"],
                    wrecks_dir,
                    status="approved",
                    redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
                )
                summary = list_wrecks(wrecks_dir)[0]
            self.assertEqual(summary["photo_count"], 1)
            self.assertEqual(summary["review_photo_count"], 1)
            reviewed_record = json.loads((record_dir / "record.json").read_text(encoding="utf-8"))
            reviewed_photo = reviewed_record["attached_photos"][0]
            self.assertEqual(list(reviewed_photo["redactions"][0]), ["points"])
            self.assertEqual(len(reviewed_photo["redactions"][0]["points"]), 4)
            self.assertEqual(summary["field_photo_previews"][0]["source"], "attached")
            self.assertEqual(
                summary["field_photo_previews"][0]["public_thumb"],
                f"/zidentyfikowane_wraki/wreck_51100000_17200000/photos/{photo['id']}/public_thumb.jpg",
            )
            report_html = (record_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("metric-strip", report_html)
            self.assertIn("2020-2025 (6 lat)", report_html)
            self.assertIn("Zdjęcia z miejsca", report_html)
            self.assertIn(f'<img src="photos/{photo["id"]}/public_thumb.jpg"', report_html)
            self.assertNotIn("original.jpg", report_html)
            self.assertNotIn("wreck-photo-form", report_html)

    def test_wreck_rendering_outputs_public_html_without_pending_or_technical_files(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            evidence_dir = record_dir / "evidence" / "abc123"
            evidence_dir.mkdir(parents=True)
            (evidence_dir / "2022.jpg").write_bytes(image_bytes())
            record = {
                "id": "wreck_51100000_17200000",
                "status": "confirmed",
                "lat": 51.1,
                "lon": 17.2,
                "labels_present": ["2020", "2021", "2022"],
                "latest_evidence": {"created_at": "2026-06-03T10:00:00Z"},
                "links": {"geoportal": "https://example.test/?a=1&b=2"},
                "evidences": [
                    {
                        "id": "abc123",
                        "created_at": "2026-06-03T10:00:00Z",
                        "path": "evidence/abc123",
                        "labels_present": ["2022"],
                        "crops": [{"label": "2022", "file": "2022.jpg"}],
                    }
                ],
                "attached_photos": [
                    {
                        "id": "photo-approved",
                        "public_review_status": "approved",
                        "original_filename": "teren & test.jpg",
                        "created_at": "2026-06-03T11:00:00Z",
                        "public_image_file": "photos/photo-approved/public.jpg",
                        "public_thumb_file": "photos/photo-approved/public_thumb.jpg",
                    },
                    {
                        "id": "photo-pending",
                        "public_review_status": "pending",
                        "original_filename": "oczekujace.jpg",
                        "public_image_file": "photos/photo-pending/public.jpg",
                        "public_thumb_file": "photos/photo-pending/public_thumb.jpg",
                    },
                ],
            }

            self.assertEqual([photo["id"] for photo in approved_attached_photos(record)], ["photo-approved"])

            render_record_html(record, record_dir)

            report_html = (record_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("2020-2022 (3 lat)", report_html)
            self.assertIn("teren &amp; test.jpg", report_html)
            self.assertIn("photos/photo-approved/public_thumb.jpg", report_html)
            self.assertNotIn("oczekujace.jpg", report_html)
            self.assertNotIn("photos/photo-pending/public.jpg", report_html)
            self.assertNotIn("metadata.json", report_html)
            self.assertNotIn("links.json", report_html)
            self.assertNotIn("data-report-photo-upload", report_html)

    def test_wreck_public_summary_uses_safe_urls_and_approved_photo_previews(self):
        record = {
            "id": "wreck_51100000_17200000",
            "status": "confirmed",
            "lat": 51.1,
            "lon": 17.2,
            "best_score": 0.91,
            "labels_present": ["2025"],
            "latest_evidence": {
                "id": "abc123",
                "path": "evidence/abc123",
                "crops": [
                    {"label": "2025", "file": "2025.jpg"},
                    {"label": "bad", "file": "../secret.jpg"},
                ],
            },
            "evidences": [{"id": "abc123"}],
            "attached_photos": [
                {
                    "id": "photo-approved",
                    "public_review_status": "approved",
                    "original_filename": "teren.jpg",
                    "public_image_file": "photos/photo-approved/public.jpg",
                    "public_thumb_file": "photos/photo-approved/public_thumb.jpg",
                },
                {
                    "id": "photo-pending",
                    "public_review_status": "pending",
                    "original_filename": "oczekujace.jpg",
                    "public_image_file": "photos/photo-pending/public.jpg",
                    "public_thumb_file": "photos/photo-pending/public_thumb.jpg",
                },
            ],
        }

        self.assertIsNone(wreck_public_file_url(record["id"], "../secret.jpg"))
        self.assertIsNone(wreck_public_file_url(record["id"], "photos//photo-approved/public.jpg"))
        self.assertEqual(
            wreck_public_file_url(record["id"], "photos/photo-approved/public.jpg"),
            "/zidentyfikowane_wraki/wreck_51100000_17200000/photos/photo-approved/public.jpg",
        )

        summary = wreck_summary(record)

        self.assertNotIn("best_score", summary)
        self.assertEqual(summary["photo_count"], 1)
        self.assertEqual(summary["review_photo_count"], 2)
        self.assertNotIn("evidence_previews", summary)
        self.assertEqual([photo["label"] for photo in summary["field_photo_previews"]], ["teren.jpg"])
        self.assertNotIn("photo-pending", json.dumps(summary, ensure_ascii=False))

    def test_wreck_public_summary_does_not_cap_popup_gallery_previews(self):
        record = {
            "id": "wreck_51100000_17200000",
            "status": "confirmed",
            "lat": 51.1,
            "lon": 17.2,
            "labels_present": ["2025"],
            "latest_evidence": {
                "id": "abc123",
                "path": "evidence/abc123",
                "crops": [{"label": f"crop-{index}", "file": f"{index}.jpg"} for index in range(8)],
            },
            "evidences": [{"id": "abc123"}],
            "attached_photos": [
                {
                    "id": f"photo-approved-{index}",
                    "public_review_status": "approved",
                    "original_filename": f"teren-{index}.jpg",
                    "public_image_file": f"photos/photo-approved-{index}/public.jpg",
                    "public_thumb_file": f"photos/photo-approved-{index}/public_thumb.jpg",
                }
                for index in range(8)
            ],
        }

        summary = wreck_summary(record)

        self.assertEqual(summary["photo_count"], 8)
        self.assertNotIn("evidence_previews", summary)
        self.assertEqual(len(summary["field_photo_previews"]), 8)
        self.assertEqual(summary["field_photo_previews"][-1]["label"], "teren-7.jpg")

    def test_wreck_photos_module_saves_private_pending_upload_contract(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_dir = root / "wreck_51100000_17200000"
            private_dir = root / "private_photos"

            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                photo = save_attached_photo(
                    upload(image_bytes(), filename="teren test!!.jpg"),
                    record_dir,
                    submission_owner="public:abc123",
                )

            self.assertEqual(photo["public_review_status"], "pending")
            self.assertEqual(photo["submission_owner"], "public:abc123")
            self.assertEqual(photo["original_filename"], "teren_test.jpg")
            self.assertNotIn("public_image_file", photo)
            self.assertNotIn("public_thumb_file", photo)
            self.assertTrue((private_dir / photo["private_original_file"]).exists())

            photo_record = json.loads((record_dir / "photos" / photo["id"] / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(photo_record["private_original_file"], photo["private_original_file"])
            self.assertEqual(attached_photo_by_id({"attached_photos": [photo]}, photo["id"]), photo)
            with self.assertRaises(FileNotFoundError):
                attached_photo_by_id({"attached_photos": [photo]}, "missing")


class WreckReviewStorageAssetTests(unittest.TestCase):
    def test_wreck_review_module_builds_items_and_applies_statuses(self):
        old_record = {
            "id": "wreck_51100000_17200000",
            "created_at": "2026-06-01T00:00:00Z",
            "updated_at": "2026-06-02T00:00:00Z",
            "public_review_status": "pending",
            "lat": 51.1,
            "lon": 17.2,
            "status": "manual",
            "attached_photos": [{}],
            "evidences": [{}, {}],
        }
        newer_record = {
            "id": "wreck_51100001_17200000",
            "created_at": "2026-06-03T00:00:00Z",
            "public_review_status": "pending",
            "lat": 51.2,
            "lon": 17.3,
            "source": "public_submission",
        }

        items = wreck_review_items([old_record, newer_record], status="pending")

        self.assertEqual([item["id"] for item in items], ["wreck_51100001_17200000", "wreck_51100000_17200000"])
        self.assertEqual(items[1]["photo_count"], 1)
        self.assertEqual(items[1]["evidence_count"], 2)

        status_text = apply_wreck_review(old_record, status="approved", updated_at="2026-06-04T00:00:00Z")

        self.assertEqual(status_text, "approved")
        self.assertEqual(old_record["updated_at"], "2026-06-04T00:00:00Z")
        self.assertIsNotNone(old_record["reviewed_at"])
        with self.assertRaisesRegex(ValueError, "status przeglądu sprawy"):
            apply_wreck_review(old_record, status="bad", updated_at="2026-06-04T00:00:00Z")

        photo = {
            "id": "photo_1",
            "created_at": "2026-06-01T00:00:00Z",
            "original_filename": "teren.jpg",
            "public_review_status": "pending",
            "public_image_file": "photos/photo_1/public.jpg",
            "public_thumb_file": "photos/photo_1/public_thumb.jpg",
        }

        pending_item = wreck_photo_review_item("wreck_51100000_17200000", photo)
        self.assertIsNone(pending_item["public_image"])
        self.assertIsNone(pending_item["public_thumb"])

        status_text = apply_wreck_photo_review(
            photo,
            status="approved",
            redactions=[{"x": 0, "y": 0, "width": 0.5, "height": 0.5}],
        )
        approved_item = wreck_photo_review_item("wreck_51100000_17200000", photo)

        self.assertEqual(status_text, "approved")
        self.assertEqual(list(photo["redactions"][0]), ["points"])
        self.assertIn("/photos/photo_1/public.jpg", approved_item["public_image"])
        with self.assertRaisesRegex(ValueError, "status przeglądu zdjęcia"):
            apply_wreck_photo_review(photo, status="bad", redactions=[])

    def test_wreck_migration_module_sets_review_defaults_without_assets(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp) / "wreck_51100000_17200000"
            record = {
                "id": "wreck_51100000_17200000",
                "created_at": "2026-06-01T00:00:00Z",
                "attached_photos": [],
            }

            changed = migrate_wreck_record(record_dir, record)

            self.assertTrue(changed)
            self.assertEqual(record["public_review_status"], "approved")
            self.assertEqual(record["reviewed_at"], "2026-06-01T00:00:00Z")
            self.assertIsNone(record["submission_owner"])
            self.assertEqual(record["redactions"], [])

    def test_wreck_assets_module_keeps_public_private_boundaries(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrecks_dir = root / "wraki"
            record_dir = wrecks_dir / "wreck_51100000_17200000"
            evidence_dir = record_dir / "evidence" / "abc123"
            approved_photo_dir = record_dir / "photos" / "photo-approved"
            pending_photo_dir = record_dir / "photos" / "photo-pending"
            private_dir = root / "private_photos"
            evidence_dir.mkdir(parents=True)
            approved_photo_dir.mkdir(parents=True)
            pending_photo_dir.mkdir(parents=True)
            (evidence_dir / "2025.jpg").write_bytes(b"evidence")
            (approved_photo_dir / "public.jpg").write_bytes(b"approved")
            (approved_photo_dir / "public_thumb.jpg").write_bytes(b"thumb")
            (pending_photo_dir / "public.jpg").write_bytes(b"pending")
            private_original = (
                private_dir / "wreck_photos" / "wreck_51100000_17200000" / "photo-approved" / "original.jpg"
            )
            private_original.parent.mkdir(parents=True)
            private_original.write_bytes(image_bytes())
            write_json(
                record_dir / "record.json",
                {
                    "id": "wreck_51100000_17200000",
                    "public_review_status": "approved",
                    "lat": 51.1,
                    "lon": 17.2,
                    "attached_photos": [
                        {
                            "id": "photo-approved",
                            "public_review_status": "approved",
                            "private_original_file": "wreck_photos/wreck_51100000_17200000/photo-approved/original.jpg",
                            "content_type": "image/jpeg",
                            "public_image_file": "photos/photo-approved/public.jpg",
                            "public_thumb_file": "photos/photo-approved/public_thumb.jpg",
                        },
                        {
                            "id": "photo-pending",
                            "public_review_status": "pending",
                            "public_image_file": "photos/photo-pending/public.jpg",
                        },
                    ],
                },
            )

            with patch.object(core_config, "PRIVATE_PHOTOS_DIR", private_dir):
                self.assertTrue(wreck_is_public("wreck_51100000_17200000", wrecks_dir))
                evidence_path, evidence_content_type = public_wreck_asset(
                    "wreck_51100000_17200000", "evidence/abc123/2025.jpg", wrecks_dir
                )
                approved_path, approved_content_type = public_wreck_asset(
                    "wreck_51100000_17200000", "photos/photo-approved/public.jpg", wrecks_dir
                )
                original_path, original_content_type = wreck_photo_original_asset(
                    "wreck_51100000_17200000", "photo-approved", wrecks_dir
                )

            self.assertEqual(evidence_path, evidence_dir / "2025.jpg")
            self.assertEqual(evidence_content_type, "image/jpeg")
            self.assertEqual(approved_path, approved_photo_dir / "public.jpg")
            self.assertEqual(approved_content_type, "image/jpeg")
            self.assertEqual(original_path, private_original)
            self.assertEqual(original_content_type, "image/jpeg")
            with self.assertRaises(FileNotFoundError):
                public_wreck_asset("wreck_51100000_17200000", "photos/photo-pending/public.jpg", wrecks_dir)
            with self.assertRaises(FileNotFoundError):
                public_wreck_asset("wreck_51100000_17200000", "../record.json", wrecks_dir)
            self.assertFalse(wreck_is_public("../wreck_51100000_17200000", wrecks_dir))

    def test_delete_wreck_removes_only_valid_record_folder(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp)
            record_dir = wrecks_dir / "wreck_51100000_17200000"
            write_json(record_dir / "record.json", {"id": "wreck_51100000_17200000", "lat": 51.1, "lon": 17.2})

            result = delete_wreck("wreck_51100000_17200000", wrecks_dir)

            self.assertEqual(result["deleted"], "wreck_51100000_17200000")
            self.assertFalse(record_dir.exists())
            with self.assertRaises(ValueError):
                delete_wreck("../wreck_51100000_17200000", wrecks_dir)

    def test_wreck_store_validates_record_directory_contract(self):
        with TemporaryDirectory() as tmp:
            wrecks_dir = Path(tmp)
            record_dir = wrecks_dir / "wreck_51100000_17200000"
            write_json(record_dir / "record.json", {"id": "wreck_51100000_17200000"})

            self.assertEqual(validate_wreck_id("wreck_51100000_17200000"), "wreck_51100000_17200000")
            self.assertEqual(record_dir_for("wreck_51100000_17200000", wrecks_dir), record_dir.resolve())

            with self.assertRaises(ValueError):
                validate_wreck_id("../wreck_51100000_17200000")
            with self.assertRaises(ValueError):
                record_dir_for("../wreck_51100000_17200000", wrecks_dir)
            with self.assertRaises(FileNotFoundError):
                record_dir_for("wreck_51100001_17200000", wrecks_dir)


if __name__ == "__main__":
    unittest.main()

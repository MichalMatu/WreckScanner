import unittest
from pathlib import Path

from app.http import routes

ROOT_DIR = Path(__file__).resolve().parents[1]


class HttpRouteParsingTests(unittest.TestCase):
    def test_asset_routes_return_expected_identifiers(self):
        self.assertEqual(
            routes.field_photo_asset_route("/api/field-photos/photo-1/public-thumb"), ("photo-1", "public-thumb")
        )
        self.assertIsNone(routes.field_photo_asset_route("/api/field-photos/photo-1/private-thumb"))

    def test_admin_photo_routes_return_scope_and_ids(self):
        self.assertEqual(
            routes.admin_photo_original_route("/api/admin/photos/field/photo-1/original"), ("field", ("photo-1",))
        )
        self.assertEqual(
            routes.admin_photo_review_route("/api/admin/photos/field/photo-1/review"), ("field", ("photo-1",))
        )
        self.assertEqual(
            routes.admin_photo_delete_route("/api/admin/photos/field/photo-1"),
            ("field", ("photo-1",)),
        )
        self.assertIsNone(routes.admin_photo_delete_route("/api/admin/photos/field/photo-1/extra"))

    def test_patch_and_static_report_routes_extract_ids(self):
        self.assertEqual(routes.field_photo_location_route("/api/field-photos/photo-1/location"), "photo-1")
        self.assertEqual(routes.field_photo_owner_original_route("/api/field-photos/photo-1/owner-original"), "photo-1")
        self.assertEqual(routes.field_photo_owner_review_route("/api/field-photos/photo-1/owner-review"), "photo-1")
        self.assertEqual(routes.admin_privacy_request_route("/api/admin/privacy-requests/request-1"), "request-1")

    def test_frontend_uses_only_canonical_admin_photo_delete_route(self):
        actions_js = (ROOT_DIR / "web" / "app" / "field_photo_actions.js").read_text(encoding="utf-8")

        self.assertIn(
            "apiDeleteJson(`${ADMIN_PHOTOS_URL}/field/${encodeURIComponent(id)}`)",
            actions_js,
        )
        self.assertNotIn(
            "apiDeleteJson(`${FIELD_PHOTOS_URL}/${encodeURIComponent(id)}`)",
            actions_js,
        )


if __name__ == "__main__":
    unittest.main()

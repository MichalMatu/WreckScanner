import unittest

from app import config as app_config
from app.http import routes


class HttpRouteParsingTests(unittest.TestCase):
    def test_wreck_package_and_upload_routes_extract_wreck_id(self):
        self.assertEqual(routes.report_package_wreck_id("/api/wrecks/wreck-1/report-package"), "wreck-1")
        self.assertEqual(
            routes.public_report_package_wreck_id("/api/wrecks/wreck-1/public-report-package"),
            "wreck-1",
        )
        self.assertEqual(routes.wreck_photo_upload_wreck_id("/api/wrecks/wreck-1/photos"), "wreck-1")
        self.assertEqual(routes.wreck_field_photo_attach_wreck_id("/api/wrecks/wreck-1/field-photos/attach"), "wreck-1")
        self.assertIsNone(routes.report_package_wreck_id("/api/wrecks/wreck-1/report-package/extra"))

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
            routes.admin_photo_original_route("/api/admin/photos/wreck/wreck-1/photo-2/original"),
            ("wreck", ("wreck-1", "photo-2")),
        )
        self.assertEqual(
            routes.admin_photo_review_route("/api/admin/photos/field/photo-1/review"), ("field", ("photo-1",))
        )
        self.assertEqual(
            routes.admin_photo_delete_route("/api/admin/photos/wreck/wreck-1/photo-2"),
            ("wreck", ("wreck-1", "photo-2")),
        )
        self.assertIsNone(routes.admin_photo_delete_route("/api/admin/photos/wreck/wreck-1/photo-2/extra"))

    def test_patch_and_static_report_routes_extract_ids(self):
        self.assertEqual(routes.admin_wreck_review_route("/api/admin/wrecks/wreck-1/review"), "wreck-1")
        self.assertEqual(routes.field_photo_location_route("/api/field-photos/photo-1/location"), "photo-1")
        self.assertEqual(routes.field_photo_owner_original_route("/api/field-photos/photo-1/owner-original"), "photo-1")
        self.assertEqual(routes.field_photo_owner_review_route("/api/field-photos/photo-1/owner-review"), "photo-1")
        self.assertEqual(routes.admin_privacy_request_route("/api/admin/privacy-requests/request-1"), "request-1")
        self.assertEqual(routes.wreck_index_wreck_id(f"/{app_config.WRECKS_ROUTE}/wreck-1/index.html"), "wreck-1")
        self.assertIsNone(routes.wreck_index_wreck_id("/wrecks/wreck-1/report.html"))


if __name__ == "__main__":
    unittest.main()

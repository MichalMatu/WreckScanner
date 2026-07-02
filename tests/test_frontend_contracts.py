from __future__ import annotations

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class FrontendContracts(unittest.TestCase):
    def test_frontend_uses_location_inspection_as_preview_only(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        location_js = (ROOT_DIR / "web" / "app" / "location_inspection.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        saved_wrecks_js = (ROOT_DIR / "web" / "app" / "saved_wrecks.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn('<script src="/app/location_inspection.js"></script>', html)
        self.assertIn("apiPostJson('/api/inspect'", location_js)
        self.assertNotIn("saveManualWreck", location_js + saved_wrecks_js)
        self.assertNotIn("inspect.saveWreck", i18n_js)
        self.assertNotIn("map-popup-text-action", location_js)
        self.assertIn("manualWrecks: 'manual_wrecks'", config_js)
        self.assertNotIn("/api/download", config_js + html)
        self.assertNotIn("/api/analyze", config_js + html)
        self.assertNotIn("scan_analysis", config_js + settings_js + html)
        self.assertNotIn("yolo_wrecks", config_js + settings_js + html)

    def test_frontend_removes_retired_map_download_and_model_controls(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        layers_js = (ROOT_DIR / "web" / "app" / "layers.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        frontend = html + config_js + layers_js + settings_js + styles + i18n_js

        for retired in (
            "model-select",
            "conf-select",
            "geotiff-cache",
            "modal-geotiff-cache",
            "btn-run",
            "context-center-scan",
            "context-toggle-crosshair",
            "YOLO",
            "GeoTIFF",
            "toggle-surface-layer",
            "admin-layer-surface",
            "SURFACE_FEATURES_URL",
            "setSurfaceLayerVisible",
            "layers.surface",
            "layer-pin--surface",
        ):
            self.assertNotIn(retired, frontend)

    def test_frontend_uses_one_vehicle_layer_for_cases_and_vehicle_photos(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        field_photos_js = (ROOT_DIR / "web" / "app" / "field_photos.js").read_text(encoding="utf-8")
        saved_wrecks_js = (ROOT_DIR / "web" / "app" / "saved_wrecks.js").read_text(encoding="utf-8")
        reports_js = (ROOT_DIR / "web" / "app" / "reports.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))
        frontend = html + config_js + settings_js + field_photos_js + saved_wrecks_js + reports_js + i18n_js + styles

        self.assertIn('id="toggle-vehicles"', html)
        self.assertIn('id="admin-layer-vehicles"', html)
        self.assertIn("vehicles: 'vehicles'", config_js)
        self.assertIn("vehicle: PUBLIC_LAYER_KEYS.vehicles", config_js)
        self.assertIn("function buildVehicleGroups", saved_wrecks_js)
        self.assertIn("function placeVehicleMarkers", saved_wrecks_js)
        self.assertIn("function toggleVehicleLayer", saved_wrecks_js)
        self.assertIn("function openVehicleCasePhotoUpload", saved_wrecks_js)
        self.assertIn("openFieldPhotoUploadModal", saved_wrecks_js)
        self.assertIn("issueType === FIELD_PHOTO_ISSUE_TYPE_VEHICLE) return false", field_photos_js)
        self.assertIn("function vehiclePhotoPopup", saved_wrecks_js)
        self.assertNotIn("function vehicleCasePopup", saved_wrecks_js)
        self.assertNotIn("function vehiclePhotoOnlyPopup", saved_wrecks_js)
        self.assertNotIn("wreck.evidence_previews", saved_wrecks_js)
        self.assertNotIn("extraPhotos", reports_js)
        self.assertNotIn("report-package-extra-photos", html)
        self.assertIn("showHeader: false", saved_wrecks_js)
        self.assertNotIn("fieldPhotoGroupMeta(group, photos)", saved_wrecks_js)
        self.assertNotIn("toFixed(6)", saved_wrecks_js)

        for retired in (
            "toggle-saved-wrecks",
            "toggle-field-photo-vehicle",
            "admin-layer-saved-wrecks",
            "admin-layer-field-photo-vehicle",
            "layers.savedWrecks",
            "layers.fieldPhotoVehicles",
            "fieldPhotoVehicle",
            "savedWrecks",
            "field_photo_vehicle",
            "layer-pin--field-photo-vehicle",
            "placeSavedWrecks",
            "toggleSavedWreckLayer",
            "clearSavedWreckMarkers",
        ):
            self.assertNotIn(retired, frontend)

    def test_field_photo_upload_keeps_edit_token_out_of_initial_form(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")
        popups_js = (ROOT_DIR / "web" / "app" / "field_photo_popups.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        frontend = html + upload_js + review_js + popups_js + i18n_js

        self.assertNotIn("field-photo-edit-token", frontend)
        self.assertNotIn("field-photo-token-section", frontend)
        self.assertNotIn("generateFieldPhotoEditToken", frontend)
        self.assertNotIn("copyFieldPhotoEditToken", frontend)
        self.assertNotIn("field-photo-ignore-exif", frontend)
        self.assertNotIn("ignore_exif_gps", frontend)
        self.assertNotIn("fallback_lat", frontend)
        self.assertNotIn("fallback_lon", frontend)
        self.assertNotIn("field-photo-fallback", frontend)
        self.assertNotIn("modal.fieldPhoto.fallbackCoords", frontend)
        self.assertNotIn("fieldPhotoSourceLabel", frontend)
        self.assertNotIn("fieldPhoto.popup.source", frontend)
        self.assertIn("ensureFieldPhotoUploadEditToken", upload_js)
        self.assertIn('id="modal-field-photo-upload" hidden onclick="closeFieldPhotoUploadModal(this)"', html)
        self.assertIn("function closeFieldPhotoUploadModal", upload_js)
        self.assertIn("fieldPhotoUploadInProgress", upload_js)
        self.assertIn("notifyFieldPhotoUploadBusy", upload_js)
        self.assertIn("fieldPhotoUploadSavedDraftPhotoIds", upload_js)
        self.assertIn("openFieldPhotoUploadSavedDraftSummary", upload_js)
        self.assertIn("modal.fieldPhoto.uploadInProgress", i18n_js)
        self.assertIn("modal.fieldPhoto.validationErrorHint", i18n_js)
        self.assertIn("modal.fieldPhotoSummary.closeUploadWithDrafts", i18n_js)
        self.assertIn("modal.fieldPhotoSummary.partialUpload", i18n_js)
        self.assertIn("field-photo-thanks-token", html)
        self.assertIn("field-photo-thanks-submit", html)
        self.assertIn("field-photo-thanks-discard", html)
        self.assertIn('id="field-photo-thanks-close"', html)
        self.assertIn('onclick="closeFieldPhotoThanksModal(this)"', html)
        self.assertIn("fieldPhotoThanksDraftRequiresDecision", upload_js)
        self.assertIn("modal.fieldPhotoSummary.closeBlocked", i18n_js)
        self.assertIn("openFieldPhotoThanksOwnerReview", upload_js)
        self.assertIn("/owner-submit", upload_js)
        self.assertIn("/owner-discard", upload_js)
        self.assertIn("openFieldPhotoOwnerReviewWithToken", review_js)
        self.assertIn('id="photo-review-close"', html)
        self.assertIn('onclick="handlePhotoReviewBackdropClose(this)"', html)
        self.assertIn("function closePhotoReviewModal", review_js)
        self.assertIn("function handlePhotoReviewBackdropClose", review_js)
        self.assertIn("photoReviewRequiresSummaryReturn", review_js)
        self.assertIn("stopImmediatePropagation", review_js)
        self.assertIn("modal.fieldPhotoThanks.reviewNow", i18n_js)
        self.assertIn("modal.fieldPhotoSummary.submit", i18n_js)
        self.assertIn("modal.fieldPhotoSummary.discard", i18n_js)
        self.assertIn("returnToFieldPhotoSummary", review_js)

    def test_approved_field_photo_popups_hide_redundant_metadata(self):
        popups_js = (ROOT_DIR / "web" / "app" / "field_photo_popups.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertNotIn("function fieldPhotoGroupMeta", popups_js)
        self.assertNotIn("fieldPhoto.popup.capturedAt", popups_js)
        self.assertNotIn("fieldPhotoGroupMeta(group, photos)", popups_js)
        self.assertIn("showHeader: false", popups_js)
        self.assertNotIn("'modal.photoPreview.photoDated': 'Photo {date}'", i18n_js)
        self.assertNotIn("'modal.photoPreview.photoDated': 'Zdjęcie {date}'", i18n_js)

    def test_script_order_keeps_inspection_after_field_photo_actions(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        self.assertLess(
            html.index('<script src="/app/field_photo_actions.js"></script>'),
            html.index('<script src="/app/location_inspection.js"></script>'),
        )
        self.assertLess(
            html.index('<script src="/app/saved_wrecks.js"></script>'),
            html.index('<script src="/app/location_inspection.js"></script>'),
        )

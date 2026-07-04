from __future__ import annotations

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class FrontendContracts(unittest.TestCase):
    def test_problem_report_uses_modal_instead_of_standalone_page(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        report_js = (ROOT_DIR / "web" / "app" / "problem_report.js").read_text(encoding="utf-8")
        static_files_py = (ROOT_DIR / "app" / "http" / "static_files.py").read_text(encoding="utf-8")
        modals_css = (ROOT_DIR / "web" / "styles" / "modals.css").read_text(encoding="utf-8")

        self.assertFalse((ROOT_DIR / "web" / "report.html").exists())
        self.assertFalse((ROOT_DIR / "web" / "privacy.html").exists())
        self.assertIn('id="modal-problem-report"', html)
        self.assertIn('id="privacy-request-form"', html)
        self.assertIn("apiPostJson('/api/privacy-requests'", report_js)
        self.assertIn("window.location.pathname === '/report'", report_js)
        self.assertIn("openProblemReportModal()", report_js)
        self.assertNotIn('<a class="app-menu-drawer-item" href="/report">', html)
        self.assertIn('onclick="openProblemReportModal(); closeAppMenu()"', html)
        self.assertIn('path in {"/privacy", "/report"}', static_files_py)
        self.assertIn('send_web_file(handler, "index.html"', static_files_py)
        self.assertIn("gap: var(--space-4);", modals_css)
        self.assertIn("color: var(--text-soft);", modals_css)
        self.assertIn("min-height: calc(var(--control-height-comfortable) * 3);", modals_css)

    def test_orthophoto_filter_is_local_user_preview_setting(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        bootstrap_js = (ROOT_DIR / "web" / "app" / "bootstrap.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))

        self.assertIn("ENHANCEMENT_SETTINGS_STORAGE_KEY", config_js + bootstrap_js + settings_js)
        self.assertIn("localStorage.setItem(ENHANCEMENT_SETTINGS_STORAGE_KEY", settings_js)
        self.assertIn("enhancementSettingsRevision = token", settings_js)
        self.assertIn("refreshOrthoLayer()", settings_js)
        self.assertNotIn("settings-lock-hint", html + styles + settings_js)
        self.assertNotIn("saveEnhancementSettings", settings_js)
        self.assertNotIn("enhancement: enhancementFormSettings()", settings_js)
        self.assertIn('id="enhancement-enabled"', html)
        self.assertNotIn('id="enhancement-enabled" checked', html)
        self.assertIn('id="enhancement-clahe" min="0.1" max="5" step="0.1" value="0.8"', html)
        self.assertIn('id="enhancement-tile" min="1" max="32" step="1" value="12"', html)
        self.assertIn('id="enhancement-p-low" min="0" max="40" step="0.5" value="1"', html)
        self.assertIn('id="enhancement-p-high" min="60" max="100" step="0.5" value="99"', html)
        self.assertIn('id="enhancement-out-low" min="0" max="120" step="1" value="5"', html)
        self.assertIn('id="enhancement-out-high" min="135" max="255" step="1" value="250"', html)
        self.assertIn('id="enhancement-decast" min="0" max="1" step="0.05" value="0.2"', html)

    def test_photo_retention_admin_status_uses_friendly_card(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_js = (ROOT_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        admin_css = (ROOT_DIR / "web" / "styles" / "admin.css").read_text(encoding="utf-8")
        modals_css = (ROOT_DIR / "web" / "styles" / "modals.css").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        frontend = html + admin_js + settings_js + admin_css + modals_css + i18n_js

        admin_modal = html.split('id="modal-admin-panel"', 1)[1].split('id="modal-photo-retention"', 1)[0]
        open_admin_panel = admin_js.split("async function openAdminPanel()", 1)[1].split("async function", 1)[0]

        self.assertIn('id="open-photo-retention"', html)
        self.assertIn('onclick="openPhotoRetentionModal()"', html)
        self.assertIn('id="modal-photo-retention"', html)
        self.assertIn('id="photo-retention-status" role="status"', html)
        self.assertNotIn('id="photo-retention-section"', admin_modal)
        self.assertIn("async function openPhotoRetentionModal()", admin_js)
        self.assertIn("loadPhotoRetentionStatus()", admin_js)
        self.assertNotIn("loadPhotoRetentionStatus", open_admin_panel)
        self.assertIn("renderPhotoRetentionReport", settings_js)
        self.assertIn("photo-retention-card", settings_js + admin_css)
        self.assertIn("photo-retention-metrics", settings_js + admin_css)
        self.assertIn(".modal--photo-retention", modals_css + admin_css)
        self.assertIn("'modal.settings.photoRetention': 'Porządkowanie oryginałów'", i18n_js)
        self.assertIn("'modal.settings.photoRetentionDryRun': 'Sprawdź bez zmian'", i18n_js)
        self.assertIn("'modal.settings.photoRetentionApply': 'Wykonaj'", i18n_js)
        self.assertIn("'modal.settings.photoRetentionScanned': 'Sprawdzone zdjęcia'", i18n_js)
        self.assertIn("'modal.settings.photoRetentionReplaced': 'Zastąpione kopią publiczną'", i18n_js)
        self.assertNotIn("admin-panel-section--retention", frontend)
        self.assertNotIn("Dry-run: scanned", frontend)
        self.assertNotIn("Applied: scanned", frontend)
        self.assertNotIn("Original retention", frontend)

    def test_admin_panel_sections_share_tokenized_surface(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        admin_css = (ROOT_DIR / "web" / "styles" / "admin.css").read_text(encoding="utf-8")

        self.assertIn("background: var(--surface-subtle);", admin_css)
        self.assertIn("color: var(--text);", admin_css)
        self.assertIn("color: var(--text-strong);", admin_css)
        self.assertNotIn("admin-panel-section--tools", html + admin_css)
        self.assertNotIn("linear-gradient(135deg, var(--primary-soft)", admin_css)
        self.assertNotIn("background: rgba(255, 255, 255, 0.045);", admin_css)

    def test_admin_panel_uses_compact_shell_and_preserves_child_flow(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        admin_js = (ROOT_DIR / "web" / "admin.js").read_text(encoding="utf-8")
        photo_review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")
        privacy_requests_js = (ROOT_DIR / "web" / "app" / "privacy_requests.js").read_text(encoding="utf-8")
        welcome_js = (ROOT_DIR / "web" / "app" / "welcome.js").read_text(encoding="utf-8")
        admin_css = (ROOT_DIR / "web" / "styles" / "admin.css").read_text(encoding="utf-8")
        modals_css = (ROOT_DIR / "web" / "styles" / "modals.css").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        frontend = (
            html
            + ui_js
            + admin_js
            + photo_review_js
            + privacy_requests_js
            + welcome_js
            + admin_css
            + modals_css
            + i18n_js
        )

        self.assertIn('class="admin-panel-stack"', html)
        self.assertIn("grid-template-columns: minmax(260px, 0.82fr) minmax(360px, 1.18fr);", admin_css)
        self.assertIn("width: min(860px, calc(100vw - 24px));", modals_css)
        self.assertIn("'modal.adminPanel.publicLayers': 'Warstwy'", i18n_js)
        self.assertIn("'modal.adminPanel.publicFeatures': 'Funkcje'", i18n_js)
        self.assertIn("'modal.adminPanel.publicFeatures': 'Features'", i18n_js)
        self.assertNotIn("Warstwy dla niezalogowanych", html + i18n_js)
        self.assertNotIn("Funkcje dla niezalogowanych", html + i18n_js)
        self.assertNotIn("Features for signed-out users", html + i18n_js)
        self.assertNotIn("Layers for signed-out users", html + i18n_js)
        self.assertIn("function topOpenModalBackdrop()", ui_js)
        self.assertIn("hideModalBackdrop(topOpenModalBackdrop());", ui_js)
        self.assertNotIn("querySelectorAll('.modal-backdrop:not([hidden])').forEach(hideModalBackdrop)", ui_js)
        self.assertIn("function openAdminChildModal(id)", admin_js)
        self.assertIn("openModal(id, { preserveOpen: isAdminPanelOpen() });", admin_js)
        self.assertIn("openAdminChildModal('modal-photo-retention')", admin_js)
        self.assertIn("openAdminChildModal('modal-photo-review')", photo_review_js)
        self.assertIn("openAdminChildModal('modal-privacy-requests')", privacy_requests_js)
        self.assertIn("openAdminChildModal('modal-help')", welcome_js)
        self.assertNotIn("closeModal(document.getElementById('modal-admin-panel'))", frontend)

    def test_admin_panel_does_not_duplicate_field_photo_upload_entry(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertNotIn('id="open-field-photo-upload"', html)
        self.assertNotIn('onclick="openFieldPhotoUploadModal()"', html)
        self.assertIn('id="panel-add-field-photo"', html)
        self.assertIn('id="context-add-field-photos"', html)
        self.assertIn('id="open-photo-review"', html)

    def test_frontend_removes_retired_vehicle_case_review_panel(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        photo_review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        review_css = (ROOT_DIR / "web" / "styles" / "review.css").read_text(encoding="utf-8")
        admin_py = (ROOT_DIR / "app" / "http" / "admin.py").read_text(encoding="utf-8")
        dispatch_py = (ROOT_DIR / "app" / "http" / "dispatch.py").read_text(encoding="utf-8")
        routes_py = (ROOT_DIR / "app" / "http" / "routes.py").read_text(encoding="utf-8")
        frontend = html + config_js + photo_review_js + vehicle_layer_js + i18n_js + review_css

        self.assertFalse((ROOT_DIR / "web" / "app" / "wreck_review.js").exists())
        self.assertFalse((ROOT_DIR / "web" / "app" / "saved_wrecks.js").exists())
        self.assertIn("function refreshVehicleLayer", vehicle_layer_js)
        for retired in (
            "open-wreck-review",
            "openWreckReviewModal",
            "modal-wreck-review",
            "modal.wreckReview",
            "icon.wreckReview",
            "wreck-review",
            "ADMIN_WRECKS_URL",
            "WRECKS_URL",
            "loadSavedWrecks",
            "savedWreckLayerData",
            "reviewWreckStatus",
        ):
            self.assertNotIn(retired, frontend)
        self.assertNotIn("/api/admin/wrecks", dispatch_py + routes_py)
        self.assertNotIn("/api/wrecks", dispatch_py + routes_py + config_js + html)
        self.assertIn("Szukaj id zdjęcia / nazwy pliku", html + i18n_js)
        self.assertIn("Search photo id / filename", i18n_js)
        for retired in (
            "photo-review-scope",
            "modal.photoReview.scopeAll",
            "modal.photoReview.scopeField",
            "Search id / case",
            "Szukaj id / sprawy",
            "filter_admin_photos_by_scope",
            "scope_filter",
            "params.set('scope'",
        ):
            self.assertNotIn(retired, frontend + admin_py)

    def test_frontend_uses_location_inspection_as_preview_only(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        location_js = (ROOT_DIR / "web" / "app" / "location_inspection.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        frontend = html + config_js + location_js + settings_js + vehicle_layer_js + i18n_js

        self.assertIn('<script src="/app/location_inspection.js"></script>', html)
        self.assertIn("apiPostJson('/api/inspect'", location_js)
        self.assertIn('id="context-inspect-location"', html)
        self.assertIn("openLocationInspectionAtContextPoint", location_js)
        self.assertNotIn("map.on('click'", location_js)
        self.assertNotIn("saveManualWreck", location_js + vehicle_layer_js)
        self.assertNotIn("inspect.saveWreck", i18n_js)
        self.assertNotIn("map-popup-text-action", location_js)
        self.assertIn("reportPackages: 'report_packages'", config_js)
        self.assertNotIn("manual_wrecks", frontend)
        self.assertNotIn("manualWrecks", frontend)
        self.assertNotIn("featureManualWrecks", frontend)
        self.assertNotIn("admin-feature-manual-wrecks", frontend)
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
        map_helpers_js = (ROOT_DIR / "web" / "map_helpers.js").read_text(encoding="utf-8")
        settings_js = (ROOT_DIR / "web" / "app" / "settings.js").read_text(encoding="utf-8")
        field_photos_js = (ROOT_DIR / "web" / "app" / "field_photos.js").read_text(encoding="utf-8")
        field_photo_upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        map_context_js = (ROOT_DIR / "web" / "app" / "map_context.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")
        reports_js = (ROOT_DIR / "web" / "app" / "reports.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))
        frontend = (
            html
            + config_js
            + map_helpers_js
            + settings_js
            + field_photos_js
            + field_photo_upload_js
            + map_context_js
            + vehicle_layer_js
            + reports_js
            + i18n_js
            + styles
        )

        self.assertIn('id="toggle-vehicles"', html)
        self.assertIn('id="admin-layer-vehicles"', html)
        self.assertIn("vehicles: 'vehicles'", config_js)
        self.assertIn("vehicle: PUBLIC_LAYER_KEYS.vehicles", config_js)
        self.assertIn("function buildVehicleGroups", vehicle_layer_js)
        self.assertIn("function placeVehicleMarkers", vehicle_layer_js)
        self.assertIn("function toggleVehicleLayer", vehicle_layer_js)
        self.assertIn("function openFieldPhotoUploadModal", field_photo_upload_js)
        self.assertIn("openFieldPhotoUploadFromPanel", html + field_photo_upload_js)
        self.assertIn("openFieldPhotoUploadAtContextPoint", html + map_context_js)
        self.assertIn("issueType === FIELD_PHOTO_ISSUE_TYPE_VEHICLE) return false", field_photos_js)
        self.assertIn("function vehiclePhotoPopup", vehicle_layer_js)
        self.assertIn("openFieldPhotoReportPackageModal", reports_js)
        self.assertIn("/api/field-photo-reports/report-package", reports_js)
        self.assertIn("formData.set('place_url', target.placeUrl || '')", reports_js)
        self.assertIn("appPlaceUrl(latNumber, lonNumber, placeZoom, { photoId: safePhotoIds[0] })", reports_js)
        self.assertIn("url.searchParams.set('photo', photoId)", map_helpers_js)
        self.assertIn("url.searchParams.delete('photo')", map_helpers_js)
        self.assertIn("pendingVehiclePhotoFocusId", vehicle_layer_js)
        self.assertIn("focusVehicleMarkerFromUrl(group, marker)", vehicle_layer_js)
        self.assertNotIn("openReportPackageModal", reports_js)
        self.assertNotIn("openWreckPhotoModal", reports_js)
        self.assertNotIn("modal-wreck-photo-upload", html)
        self.assertNotIn("modal.wreckPhoto", i18n_js)
        self.assertNotIn("scopeWreck", frontend)
        self.assertNotIn("function vehicleCasePopup", vehicle_layer_js)
        self.assertNotIn("function vehicleCaseActions", vehicle_layer_js)
        self.assertNotIn("function openVehicleCasePhotoUpload", vehicle_layer_js)
        self.assertNotIn("createWreckForFieldPhotoGroup", frontend)
        self.assertNotIn("attachFieldPhotoGroupToWreck", frontend)
        self.assertNotIn("function vehiclePhotoOnlyPopup", vehicle_layer_js)
        self.assertNotIn("wreck.evidence_previews", vehicle_layer_js)
        self.assertNotIn("extraPhotos", reports_js)
        self.assertNotIn("report-package-extra-photos", html)
        self.assertNotIn("report-package-recipient", html + reports_js)
        self.assertNotIn("report-package-subject", html + reports_js)
        self.assertNotIn("report-package-body", html + reports_js)
        self.assertNotIn("copyReportEmailDraft", html + reports_js)
        self.assertNotIn('id="crop-select"', html)
        self.assertNotIn("modal.settings.crop", i18n_js)
        self.assertIn('id="report-crop-select"', html)
        self.assertIn('name="crop_m"', html)
        self.assertIn("modal.report.crop", i18n_js)
        self.assertIn("data.zip_filename", reports_js)
        self.assertIn("data.pdf_filename", reports_js)
        self.assertNotIn("reportDownloadName", reports_js)
        self.assertIn("submit.hidden = true", reports_js)
        self.assertIn("showHeader: false", vehicle_layer_js)
        self.assertNotIn("fieldPhotoGroupMeta(group, photos)", vehicle_layer_js)
        self.assertNotIn("toFixed(6)", vehicle_layer_js)

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

    def test_field_photo_panel_pick_uses_map_hint_after_closing_menu(self):
        html = (ROOT_DIR / "web" / "index.html").read_text(encoding="utf-8")
        upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        map_context_js = (ROOT_DIR / "web" / "app" / "map_context.js").read_text(encoding="utf-8")
        map_css = (ROOT_DIR / "web" / "styles" / "map.css").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn('id="map-field-photo-pick-hint"', html)
        self.assertIn("updateFieldPhotoLocationPickHintUi", upload_js)
        self.assertIn("if (typeof closeAppMenu === 'function') closeAppMenu();", upload_js)
        self.assertIn("is-picking-field-photo-location", upload_js + map_css)
        self.assertIn("cursor: crosshair !important;", map_css)
        self.assertIn("cancelFieldPhotoLocationPick({ clearStatus: true })", html + map_context_js)
        self.assertIn("panel.addPhotoPickCancel", html + i18n_js)
        self.assertNotIn("statusEl.textContent = t('panel.addPhotoPickStatus')", upload_js)

    def test_cadastral_popup_uses_ready_data_without_blocked_geoportal_link(self):
        map_context_js = (ROOT_DIR / "web" / "app" / "map_context.js").read_text(encoding="utf-8")
        i18n_js = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn("function cadastralParcelClipboardText", map_context_js)
        self.assertIn("function cadastralParcelPopup", map_context_js)
        self.assertIn("context.parcelCopyData", map_context_js + i18n_js)
        self.assertNotIn("cadastralParcelGeoportalUrl", map_context_js)
        self.assertNotIn("parcelOpenGeoportal", map_context_js + i18n_js)
        self.assertNotIn("identifyParcel=", map_context_js)

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
            html.index('<script src="/app/vehicle_layer.js"></script>'),
            html.index('<script src="/app/location_inspection.js"></script>'),
        )

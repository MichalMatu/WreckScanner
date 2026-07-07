from __future__ import annotations

import unittest
from pathlib import Path

from tests.test_frontend_contracts import read_i18n_bundle, read_index_html

ROOT_DIR = Path(__file__).resolve().parents[1]


class VehicleInsuranceFrontendTests(unittest.TestCase):
    def test_vehicle_insurance_ufg_badge_is_shared_and_editable(self):
        html = read_index_html()
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        popups_js = (ROOT_DIR / "web" / "app" / "popups.js").read_text(encoding="utf-8")
        field_photo_popups_js = (ROOT_DIR / "web" / "app" / "field_photo_popups.js").read_text(encoding="utf-8")
        upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        review_js = (ROOT_DIR / "web" / "app" / "photo_review.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")
        popups_css = (ROOT_DIR / "web" / "styles" / "popups.css").read_text(encoding="utf-8")
        forms_css = (ROOT_DIR / "web" / "styles" / "forms.css").read_text(encoding="utf-8")
        modals_css = (ROOT_DIR / "web" / "styles" / "modals.css").read_text(encoding="utf-8")
        review_css = (ROOT_DIR / "web" / "styles" / "review.css").read_text(encoding="utf-8")
        i18n_js = read_i18n_bundle()
        frontend = html + config_js + popups_js + field_photo_popups_js + upload_js + review_js + i18n_js

        self.assertIn("const UFG_OC_CHECK_URL = 'https://www.ufg.pl/';", config_js)
        self.assertIn("FIELD_PHOTO_VEHICLE_INSURANCE_STATUSES", config_js)
        self.assertIn('id="field-photo-insurance-section"', html)
        self.assertIn('id="field-photo-insurance-status"', html)
        self.assertIn('id="photo-review-vehicle-insurance-section"', html)
        self.assertIn('id="photo-review-vehicle-insurance"', html)
        self.assertIn('name="photo-review-vehicle-insurance-status"', html)
        self.assertIn('id="photo-review-vehicle-insurance-checked"', html)
        self.assertIn('id="photo-review-status" hidden', html)
        self.assertIn('href="https://www.ufg.pl/" target="_blank"', html)
        self.assertIn("function vehicleInsuranceHeaderBadge", popups_js)
        self.assertIn("function humanDateTimeText", popups_js)
        self.assertIn("function humanDateText", popups_js)
        self.assertIn("${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}", popups_js)
        self.assertIn("checkedDate ? 'fieldPhoto.vehicleInsurance.badge.checked'", popups_js)
        self.assertIn(": 'fieldPhoto.vehicleInsurance.badge.checkedMissing'", popups_js)
        self.assertNotIn("function vehicleInsuranceCheckedBadge", popups_js)
        self.assertNotIn("new Intl.DateTimeFormat(document.documentElement.lang", popups_js)
        self.assertIn("function vehicleGroupInsuranceStatus", vehicle_layer_js)
        self.assertIn("function vehicleGroupInsuranceCheckedAt", vehicle_layer_js)
        self.assertNotIn("vehicleInsuranceCheckedBadge", vehicle_layer_js)
        self.assertNotIn('class="map-popup-photo-tile"', popups_js)
        self.assertIn('class="map-popup-photo"', popups_js)
        self.assertNotIn("${vehicleInsuranceUfgBadge(photo)}", popups_js)
        self.assertIn("href: UFG_OC_CHECK_URL", popups_js)
        self.assertIn('href="${escapeHtml(badge.href)}"', popups_js)
        self.assertNotIn(
            "vehicleInsuranceStatus: fieldPhotoIssueType(photo) === FIELD_PHOTO_ISSUE_TYPE_VEHICLE",
            field_photo_popups_js,
        )
        self.assertIn("formData.append('vehicle_insurance_status'", upload_js)
        self.assertIn("photoReviewVehicleInsurancePayload", review_js)
        self.assertIn("photoReviewVehicleInsuranceInputs", review_js)
        self.assertIn("setPhotoReviewStatusMessage", review_js)
        self.assertNotIn("modal.photoReview.drawHint", review_js)
        self.assertIn("vehicle_insurance_status", review_js)
        self.assertIn("vehicle_insurance_checked_at", review_js)
        self.assertIn(".map-popup-head-value--insurance-insured", popups_css)
        self.assertIn(".map-popup-head-value--insurance-uninsured", popups_css)
        self.assertNotIn(".map-popup-head-value--insurance-checked", popups_css)
        self.assertIn("max-width: min(62%, 260px);", popups_css)
        self.assertIn("white-space: nowrap;", popups_css)
        self.assertNotIn(".map-popup-ufg-link", popups_css)
        self.assertIn(".field-photo-insurance-head", forms_css)
        self.assertIn(".photo-review-insurance", review_css)
        self.assertIn(".photo-review-insurance-options", review_css)
        self.assertIn(".photo-review-insurance-option:has(input:checked)", review_css)
        self.assertIn("overflow: hidden;", modals_css)
        self.assertIn(".modal--photo-review", modals_css)
        self.assertIn("--photo-review-canvas-max-height", review_css)
        self.assertIn(".photo-review-editor:has(.photo-review-insurance:not([hidden]))", review_css)
        self.assertIn("max-height: var(--photo-review-canvas-max-height);", review_css)
        self.assertIn("margin-top: auto;", review_css)
        self.assertNotIn(
            "max-height: 560px;\n}", review_css.split(".photo-review-list", 1)[1].split(".privacy-request-list", 1)[0]
        )
        self.assertNotIn('<select class="modal-input" id="photo-review-vehicle-insurance">', html)
        self.assertNotIn("Admin zapisuje ten wynik", frontend)
        self.assertNotIn("Narysuj obszar na danych do zamazania", frontend)
        self.assertNotIn("modal.photoReview.vehicleInsuranceHint", frontend)
        self.assertNotIn("modal.photoReview.drawHint", frontend)
        self.assertIn("'fieldPhoto.vehicleInsurance.badge.checked': 'UFG: {date}'", i18n_js)
        self.assertIn("'fieldPhoto.vehicleInsurance.badge.checkedMissing': 'UFG'", i18n_js)
        self.assertNotIn("fieldPhoto.vehicleInsurance.badge.insured", i18n_js)
        self.assertNotIn("fieldPhoto.vehicleInsurance.badge.uninsured", i18n_js)
        self.assertNotIn("UFG yes", i18n_js)
        self.assertNotIn("UFG tak", i18n_js)
        self.assertNotIn("UFG: insured", i18n_js)
        self.assertNotIn("UFG: OC", i18n_js)
        self.assertNotIn("UFG: brak OC", i18n_js)
        self.assertIn("'fieldPhoto.vehicleInsurance.ufgTitle': 'UFG: {status}'", i18n_js)
        self.assertIn("'fieldPhoto.vehicleInsurance.ufgCheckedTitle': 'UFG: {status}, {date}'", i18n_js)
        self.assertNotIn("Open insurance check", i18n_js)
        self.assertNotIn("Otwórz sprawdzenie OC", i18n_js)
        for key in (
            "fieldPhoto.vehicleInsurance.unknown",
            "fieldPhoto.vehicleInsurance.insured",
            "fieldPhoto.vehicleInsurance.uninsured",
            "fieldPhoto.vehicleInsurance.badge.checked",
            "fieldPhoto.vehicleInsurance.badge.checkedMissing",
            "fieldPhoto.vehicleInsurance.ufgTitle",
            "fieldPhoto.vehicleInsurance.ufgCheckedTitle",
            "modal.photoReview.vehicleInsurance",
            "modal.photoReview.vehicleInsuranceCheckedAt",
            "modal.photoReview.vehicleInsuranceCheckedPending",
        ):
            self.assertIn(key, frontend)

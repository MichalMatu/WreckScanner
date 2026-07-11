from __future__ import annotations

import re
import unittest
from pathlib import Path

from app.http import static_files

ROOT_DIR = Path(__file__).resolve().parents[1]


class UiAccessibilityFrontendContracts(unittest.TestCase):
    def test_dynamic_statuses_are_live_and_global_status_is_outside_drawer(self):
        html = static_files.render_web_template("index.html")
        for status_id in (
            "status",
            "admin-login-status",
            "settings-save-status",
            "admin-public-features-status",
            "admin-map-view-status",
            "admin-public-layers-status",
            "photo-retention-status",
            "field-photo-status",
            "field-photo-thanks-status",
            "field-photo-owner-status",
            "photo-review-status",
            "privacy-request-status",
            "privacy-request-submit-status",
            "report-pdf-status",
        ):
            self.assertRegex(
                html,
                rf'id="{re.escape(status_id)}"[^>]*role="status"[^>]*aria-live="polite"',
                status_id,
            )
        self.assertGreater(html.index('id="status"'), html.index("</aside>"))
        self.assertIn('aria-atomic="true"', html)

    def test_modal_manager_and_reduced_motion_are_part_of_the_frontend_contract(self):
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        base_css = (ROOT_DIR / "web" / "styles" / "base.css").read_text(encoding="utf-8")

        self.assertIn("dialog.setAttribute('role', 'dialog')", ui_js)
        self.assertIn("dialog.setAttribute('aria-modal', 'true')", ui_js)
        self.assertIn("dialog.setAttribute('aria-labelledby', title.id)", ui_js)
        self.assertIn("const modalFocusStack = [];", ui_js)
        self.assertIn("function syncPageIsolation()", ui_js)
        self.assertIn("function cycleOverlayFocus(event, elements)", ui_js)
        self.assertIn("restoreOverlayFocus(state?.returnFocus)", ui_js)
        self.assertIn("@media (prefers-reduced-motion: reduce)", base_css)

    def test_critical_map_controls_have_localized_accessible_names(self):
        html = static_files.render_web_template("index.html")
        i18n = "\n".join((ROOT_DIR / "web" / path).read_text(encoding="utf-8") for path in ("i18n/pl.js", "i18n/en.js"))

        self.assertIn('<main id="map" tabindex="0" aria-label="Interaktywna mapa"', html)
        self.assertIn('id="year-range"', html)
        self.assertIn('data-i18n-attr="aria-label:panel.baseMapSlider"', html)
        self.assertIn("title:panel.baseMapPrevious;aria-label:panel.baseMapPrevious", html)
        self.assertIn("title:panel.baseMapNext;aria-label:panel.baseMapNext", html)
        self.assertIn("placeholder:modal.photoReview.search;aria-label:modal.photoReview.search", html)
        for key in ("map.label", "panel.baseMapSlider", "panel.baseMapPrevious", "panel.baseMapNext"):
            self.assertEqual(i18n.count(f"'{key}'"), 2)

    def test_field_photo_location_picker_has_a_keyboard_contract(self):
        html = static_files.render_web_template("index.html")
        upload_js = (ROOT_DIR / "web" / "app" / "field_photo_upload.js").read_text(encoding="utf-8")
        map_css = (ROOT_DIR / "web" / "styles" / "map.css").read_text(encoding="utf-8")
        i18n = "\n".join((ROOT_DIR / "web" / path).read_text(encoding="utf-8") for path in ("i18n/pl.js", "i18n/en.js"))

        self.assertRegex(html, r'<main id="map" tabindex="0"')
        self.assertIn("function focusFieldPhotoLocationPicker()", upload_js)
        self.assertIn("function handleFieldPhotoLocationPickKeydown(event)", upload_js)
        self.assertIn("function handleFieldPhotoLocationPickEscape(event)", upload_js)
        self.assertIn("event.target !== fieldPhotoLocationPickMapContainer()", upload_js)
        self.assertIn("event.key !== 'Enter' && event.key !== ' '", upload_js)
        self.assertIn("void chooseFieldPhotoLocation(map.getCenter())", upload_js)
        self.assertIn("cancelFieldPhotoLocationPick({ announce: true, restoreFocus: true })", upload_js + html)
        self.assertIn("mapContainer.setAttribute('aria-keyshortcuts', 'Enter Space Escape')", upload_js)
        self.assertIn("mapContainer.focus({ preventScroll: true })", upload_js)
        self.assertIn(".leaflet-container.is-picking-field-photo-location::after", map_css)
        for key in ("panel.addPhotoPickMapLabel", "panel.addPhotoPickCancelled"):
            self.assertEqual(i18n.count(f"'{key}'"), 2)

    def test_language_deep_link_and_short_viewport_popup_are_supported(self):
        i18n_runtime = (ROOT_DIR / "web" / "i18n.js").read_text(encoding="utf-8")
        popup_css = (ROOT_DIR / "web" / "styles" / "popups.css").read_text(encoding="utf-8")

        self.assertIn("new URLSearchParams(window.location.search).get('lang')", i18n_runtime)
        self.assertIn("requested === 'pl' || requested === 'en'", i18n_runtime)
        self.assertIn("@media (max-height: 520px)", popup_css)
        self.assertIn("max-height: calc(100vh - 112px)", popup_css)
        self.assertIn("overflow-y: auto", popup_css)
        self.assertIn("aspect-ratio: 16 / 7", popup_css)


if __name__ == "__main__":
    unittest.main()

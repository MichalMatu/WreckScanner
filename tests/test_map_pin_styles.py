import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class MapPinStyleContracts(unittest.TestCase):
    def test_vehicle_pin_uses_group_insurance_status_as_ring(self):
        css = (ROOT_DIR / "web" / "styles" / "map_pins.css").read_text(encoding="utf-8")
        tokens_css = (ROOT_DIR / "web" / "styles" / "tokens.css").read_text(encoding="utf-8")
        markers_js = (ROOT_DIR / "web" / "app" / "map_markers.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")

        self.assertIn(
            "vehicleIcon(photoCount = 0, reviewStatus = 'approved', insuranceStatus = "
            "FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN)",
            markers_js,
        )
        self.assertIn("FIELD_PHOTO_VEHICLE_INSURANCE_STATUSES.has(insuranceStatus)", markers_js)
        self.assertIn("vehicle-pin--insurance-${safeInsuranceStatus}", markers_js)
        self.assertIn(
            "vehicleIcon(vehicleGroupPhotoCount(group), 'approved', vehicleGroupInsuranceStatus(group))",
            vehicle_layer_js,
        )
        for status in ("unknown", "insured", "uninsured"):
            self.assertIn(f"--pin-insurance-{status}-ring:", tokens_css)
            self.assertIn(f".vehicle-pin--insurance-{status}", css)
        self.assertIn("border: 3px solid var(--pin-vehicle-current-ring);", css)
        self.assertIn("box-shadow: var(--pin-dot-shadow), 0 0 0 2px var(--pin-vehicle-current-ring-soft);", css)

    def test_low_zoom_dot_mode_uses_distinct_shapes_for_place_types(self):
        css = (ROOT_DIR / "web" / "styles" / "map_pins.css").read_text(encoding="utf-8")

        self.assertIn(".marker-detail--dots .vehicle-pin {", css)
        self.assertIn("width: 16px;", css)
        self.assertIn("border: 3px solid var(--pin-vehicle-current-ring);", css)
        self.assertIn(".marker-detail--dots .field-photo-pin--infrastructure {", css)
        self.assertIn("transform: translate(10px, 27px) rotate(45deg);", css)
        self.assertIn(".marker-detail--dots .field-photo-pin--smoke {", css)
        self.assertIn("height: 10px;", css)
        self.assertIn("border-radius: var(--radius-full);", css)
        self.assertIn(".marker-detail--dots .pending-submission-pin {", css)
        self.assertIn("border: 2px dashed var(--pin-pending-ring);", css)
        self.assertNotIn("width: 12px;\n    height: 12px;\n    border-radius: 50%;", css)

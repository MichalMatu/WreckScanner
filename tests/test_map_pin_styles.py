import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class MapPinStyleContracts(unittest.TestCase):
    def test_vehicle_pin_uses_group_insurance_status_as_ring(self):
        html = (ROOT_DIR / "web" / "partials" / "app_shell.html").read_text(encoding="utf-8")
        css = (ROOT_DIR / "web" / "styles" / "map_pins.css").read_text(encoding="utf-8")
        layer_css = (ROOT_DIR / "web" / "styles" / "map_layers.css").read_text(encoding="utf-8")
        tokens_css = (ROOT_DIR / "web" / "styles" / "tokens.css").read_text(encoding="utf-8")
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        markers_js = (ROOT_DIR / "web" / "app" / "map_markers.js").read_text(encoding="utf-8")
        vehicle_layer_js = (ROOT_DIR / "web" / "app" / "vehicle_layer.js").read_text(encoding="utf-8")
        i18n_js = "\n".join(
            (ROOT_DIR / "web" / path).read_text(encoding="utf-8") for path in ("i18n/pl.js", "i18n/en.js")
        )

        self.assertIn("function vehicleIcon(", markers_js)
        self.assertIn("insuranceStatus = FIELD_PHOTO_VEHICLE_INSURANCE_STATUS_UNKNOWN", markers_js)
        self.assertIn("isLongStanding = false", markers_js)
        self.assertIn("FIELD_PHOTO_VEHICLE_INSURANCE_STATUSES.has(insuranceStatus)", markers_js)
        self.assertIn("vehicle-pin--insurance-${safeInsuranceStatus}", markers_js)
        self.assertIn("const VEHICLE_LONG_STANDING_DEFAULT_DAYS = 30;", config_js)
        self.assertIn("const VEHICLE_LONG_STANDING_DAY_OPTIONS = [30, 45, 60];", config_js)
        self.assertIn("VEHICLE_LONG_STANDING_DAYS_STORAGE_KEY", config_js)
        self.assertIn("vehicle-pin--long-standing", markers_js + css)
        self.assertIn("function vehicleGroupIsLongStanding", vehicle_layer_js)
        self.assertIn("fieldPhotoGroupStartTimestamp(group.photos, nowMs)", vehicle_layer_js)
        self.assertIn("function vehicleLongStandingMs", vehicle_layer_js)
        self.assertNotIn("VEHICLE_LONG_STANDING_MS", config_js + vehicle_layer_js)
        self.assertIn(
            "vehicleGroupIsLongStanding(group)",
            vehicle_layer_js,
        )
        self.assertIn("const VEHICLE_STATUS_FILTER_ALL = 'all';", vehicle_layer_js)
        self.assertIn("const VEHICLE_MARKER_BASE_Z_INDEX = 1200;", vehicle_layer_js)
        self.assertIn("function vehicleGroupMatchesStatusFilter", vehicle_layer_js)
        self.assertIn("function visibleVehicleGroups", vehicle_layer_js)
        self.assertIn("function vehicleGroupStatusPriority", vehicle_layer_js)
        self.assertIn("function vehicleGroupZIndexOffset", vehicle_layer_js)
        self.assertIn("function prioritizedVehicleGroups", vehicle_layer_js)
        self.assertIn("prioritizedVehicleGroups().forEach", vehicle_layer_js)
        self.assertIn("zIndexOffset: vehicleGroupZIndexOffset(group)", vehicle_layer_js)
        self.assertIn("function setVehicleStatusFilter", vehicle_layer_js)
        self.assertIn("function vehicleStatusCounts", vehicle_layer_js)
        self.assertIn("function updateVehicleStatusLegendCounts", vehicle_layer_js)
        self.assertIn("function setVehicleLongStandingDays", vehicle_layer_js)
        self.assertIn("function updateVehicleLongStandingThresholdControls", vehicle_layer_js)
        self.assertIn("function vehicleMarkerTitle", vehicle_layer_js)
        self.assertIn("title: markerTitle", vehicle_layer_js)
        self.assertIn("alt: markerTitle", vehicle_layer_js)
        self.assertIn("marker.bindTooltip(markerTitle", vehicle_layer_js)
        self.assertIn("vehicle.markerInsurance", i18n_js)
        self.assertIn(
            "visibleVehicleGroups().length", (ROOT_DIR / "web" / "app" / "field_photos.js").read_text(encoding="utf-8")
        )
        self.assertIn(
            "updateVehicleStatusLegendCounts()",
            (ROOT_DIR / "web" / "app" / "field_photos.js").read_text(encoding="utf-8"),
        )
        self.assertIn('class="vehicle-status-filter"', html)
        self.assertIn('data-vehicle-status-filter="uninsured"', html)
        self.assertIn('data-vehicle-status-filter="long-standing"', html)
        self.assertIn('data-vehicle-status-filter="unknown"', html)
        self.assertIn('class="vehicle-age-threshold"', html)
        self.assertIn('data-vehicle-long-standing-days="45"', html)
        self.assertIn("data-vehicle-long-standing-label", html)
        self.assertIn(".vehicle-status-filter-option.is-active", layer_css)
        self.assertIn(".vehicle-age-threshold-option.is-active", layer_css)
        self.assertIn("vehicle-status-count-uninsured", html)
        self.assertIn("vehicle-status-count-long-standing", html)
        self.assertIn(".map-pin-legend-count", layer_css)
        self.assertIn(".leaflet-tooltip.vehicle-marker-tooltip", css)
        self.assertIn("layers.vehicleStatusCountTooltip", i18n_js)
        self.assertIn("layers.vehicleStatusFilter", html + i18n_js)
        self.assertIn("layers.vehicleStatusFilterUninsured", html + i18n_js)
        self.assertIn("layers.vehicleLongStandingThreshold", html + i18n_js)
        self.assertIn("layers.vehicleLongStandingOption", i18n_js)
        for status in ("unknown", "insured", "uninsured"):
            self.assertIn(f"--pin-insurance-{status}-ring:", tokens_css)
            self.assertIn(f".vehicle-pin--insurance-{status}", css)
        self.assertIn("border: 3px solid var(--pin-vehicle-current-ring);", css)
        self.assertIn("box-shadow: var(--pin-dot-shadow), 0 0 0 2px var(--pin-vehicle-current-ring-soft);", css)
        self.assertIn('class="map-pin-legend"', html)
        self.assertIn("layers.vehicleStatusLegend", html + i18n_js)
        self.assertIn("layers.vehicleLongStandingLegend", html + i18n_js)
        self.assertIn("map-pin-age-dot", html + layer_css)
        for status in ("unknown", "insured", "uninsured"):
            self.assertIn(f"map-pin-status-ring--{status}", html + layer_css)

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

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class MapPinStyleContracts(unittest.TestCase):
    def test_low_zoom_dot_mode_uses_distinct_shapes_for_place_types(self):
        css = (ROOT_DIR / "web" / "styles" / "map_pins.css").read_text(encoding="utf-8")

        self.assertIn(".marker-detail--dots .vehicle-pin {", css)
        self.assertIn("width: 16px;", css)
        self.assertIn("border: 3px solid var(--pin-vehicle-ring);", css)
        self.assertIn(".marker-detail--dots .field-photo-pin--infrastructure {", css)
        self.assertIn("transform: translate(10px, 27px) rotate(45deg);", css)
        self.assertIn(".marker-detail--dots .field-photo-pin--smoke {", css)
        self.assertIn("height: 10px;", css)
        self.assertIn("border-radius: var(--radius-full);", css)
        self.assertIn(".marker-detail--dots .pending-submission-pin {", css)
        self.assertIn("border: 2px dashed var(--pin-pending-ring);", css)
        self.assertNotIn("width: 12px;\n    height: 12px;\n    border-radius: 50%;", css)

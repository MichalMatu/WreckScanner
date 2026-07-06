from __future__ import annotations

import unittest
from pathlib import Path

from app.http import static_files

ROOT_DIR = Path(__file__).resolve().parents[1]


def read_index_html() -> str:
    return static_files.render_web_template("index.html")


def read_i18n_bundle() -> str:
    return "\n".join(
        (ROOT_DIR / "web" / path).read_text(encoding="utf-8") for path in ("i18n/pl.js", "i18n/en.js")
    )


class ParkingCostsFrontendContracts(unittest.TestCase):
    def test_parking_costs_modal_uses_segmented_sections(self):
        html = read_index_html()
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        styles = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT_DIR / "web" / "styles").glob("*.css"))
        i18n_js = read_i18n_bundle()

        self.assertIn('onclick="openParkingCostsModal(); closeAppMenu()"', html)
        self.assertIn('id="modal-parking-costs"', html)
        self.assertIn('class="modal modal--parking-costs"', html)
        self.assertIn('class="parking-costs-tabs" role="tablist"', html)
        self.assertEqual(html.count('data-parking-costs-tab="'), 5)
        self.assertEqual(html.count('data-parking-costs-panel="'), 5)
        self.assertIn('data-i18n="modal.parkingCosts.menu"', html)
        self.assertIn("function setParkingCostsTab(tab)", ui_js)
        self.assertIn("function openParkingCostsModal()", ui_js)
        self.assertIn(".parking-costs-tab.is-active", styles)
        self.assertIn("background: var(--primary-soft);", styles)
        self.assertIn(
            "'modal.parkingCosts.numbersItem3': 'Oszacujemy wartość jednego miejsca postojowego pod blokiem.'",
            i18n_js,
        )
        self.assertIn(
            "'modal.parkingCosts.numbersItem3': 'We will estimate the value of one residential parking space.'",
            i18n_js,
        )


if __name__ == "__main__":
    unittest.main()

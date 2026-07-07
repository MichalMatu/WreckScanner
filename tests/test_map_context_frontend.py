from __future__ import annotations

import unittest
from pathlib import Path

from app.http import static_files

ROOT_DIR = Path(__file__).resolve().parents[1]


def read_index_html() -> str:
    return static_files.render_web_template("index.html")


def read_i18n_bundle() -> str:
    return "\n".join(
        (ROOT_DIR / "web" / path).read_text(encoding="utf-8") for path in ("i18n/pl.js", "i18n/en.js", "i18n.js")
    )


class MapContextFrontendContracts(unittest.TestCase):
    def test_map_context_menu_keeps_only_location_actions(self):
        html = read_index_html()
        frontend = html + (ROOT_DIR / "web" / "app" / "map_context.js").read_text(encoding="utf-8")
        frontend += (ROOT_DIR / "web" / "styles" / "map.css").read_text(encoding="utf-8") + read_i18n_bundle()

        for expected in (
            'class="context-menu-coords" id="context-menu-coords"',
            'id="context-menu-coords-value"',
            "contextMenuCoordsValue.textContent",
            'onclick="copyContextPlaceLink()"',
            'onclick="copyContextCoords()"',
            'id="context-show-address"',
            'onclick="showAddressAtContextPoint()"',
            "ADDRESS_REVERSE_URL",
            "context.addressTitle",
            "context.addressSource",
        ):
            self.assertIn(expected, frontend)
        for retired in (
            'data-i18n="context.copyCoords"',
            "button:not([hidden])')?.focus",
            "openMapSourcePanelFromContext",
            "context.changeBaseMap",
            "map-context-secondary",
            "border-top: 1px solid var(--border) !important;",
            "border-bottom: 1px solid var(--border);",
        ):
            self.assertNotIn(retired, frontend)


if __name__ == "__main__":
    unittest.main()

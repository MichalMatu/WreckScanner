from __future__ import annotations

import unittest
from pathlib import Path

from app.http import static_files

ROOT_DIR = Path(__file__).resolve().parents[1]


def read_index_html() -> str:
    return static_files.render_web_template("index.html")


class AppMenuFrontendContracts(unittest.TestCase):
    def test_app_menu_uses_compact_footer_actions(self):
        html = read_index_html()
        ui_js = (ROOT_DIR / "web" / "ui.js").read_text(encoding="utf-8")
        panel_css = (ROOT_DIR / "web" / "styles" / "panel.css").read_text(encoding="utf-8")
        tokens_css = (ROOT_DIR / "web" / "styles" / "tokens.css").read_text(encoding="utf-8")

        self.assertIn('id="app-menu-toggle-lang"', html)
        self.assertIn('id="app-menu-lang-label"', html)
        self.assertIn('class="app-menu-footer-links"', html)
        self.assertIn('class="app-menu-footer-actions"', html)
        self.assertIn('class="app-menu-footer-link"', html)
        self.assertIn('class="app-menu-footer-icon app-menu-footer-icon--settings"', html)
        self.assertIn('class="app-menu-footer-icon app-menu-footer-icon--lang btn-lang"', html)
        self.assertIn('class="app-menu-footer-icon app-menu-footer-icon--admin"', html)
        self.assertLess(html.index('class="app-menu-footer-actions"'), html.index('class="app-menu-footer-links"'))
        self.assertIn('data-i18n-attr="title:icon.settings;aria-label:icon.settings"', html)
        self.assertIn('data-i18n-attr="title:icon.lang;aria-label:icon.lang"', html)
        self.assertIn('onclick="openSettingsModal(); closeAppMenu()"', html)
        self.assertIn('onclick="toggleLang()"', html)
        self.assertIn("onclick=\"openModal('modal-privacy-info'); closeAppMenu()\"", html)
        self.assertIn('onclick="openProblemReportModal(); closeAppMenu()"', html)
        self.assertIn("function toggleLang()", ui_js)
        self.assertIn("document.querySelectorAll('.lang-label')", ui_js)
        self.assertIn(".app-menu-footer-links", panel_css)
        self.assertIn(".app-menu-footer-actions", panel_css)
        self.assertIn(".app-menu-footer-link", panel_css)
        self.assertIn(".app-menu-footer-icon", panel_css)
        self.assertIn(".app-menu-footer-icon--lang", panel_css)
        self.assertIn(".app-menu-footer-icon--admin.is-admin", panel_css)
        self.assertIn(".app-menu-drawer-section", panel_css)
        self.assertNotIn('data-i18n="icon.settings">Ustawienia</span>', html)

        map_panel_css = panel_css.split(".app-menu-map-panel {", 1)[1].split("}", 1)[0]
        drawer_section_css = panel_css.split(".app-menu-drawer-section {", 1)[1].split("}", 1)[0]
        footer_css = panel_css.split(".app-menu-drawer-footer {", 1)[1].split("}", 1)[0]
        self.assertIn("--app-menu-item-gap: 7px;", panel_css)
        self.assertIn("width: min(310px, calc(100vw - 44px));", panel_css)
        self.assertIn("width: min(280px, calc(100vw - 32px));", panel_css)
        self.assertIn("justify-content: flex-end;", panel_css)
        self.assertIn("margin-left: auto;", panel_css)
        self.assertIn("text-align: right;", panel_css)
        self.assertIn("gap: var(--app-menu-item-gap);", map_panel_css)
        self.assertIn("padding: 0 var(--space-5) var(--app-menu-item-gap);", map_panel_css)
        self.assertIn("gap: var(--app-menu-item-gap);", drawer_section_css)
        self.assertIn("grid-template-columns: 1fr;", footer_css)
        self.assertIn("flex-wrap: nowrap;", panel_css)
        self.assertIn("padding-top: var(--space-2);", panel_css)
        self.assertNotIn("padding: var(--space-2) 0;", drawer_section_css)
        self.assertNotIn("border-top:", drawer_section_css)
        self.assertIn("border: 1px solid var(--border);", panel_css)
        self.assertIn("border-radius: var(--radius-md);", panel_css)
        self.assertIn("background: var(--surface-subtle);", panel_css)
        self.assertNotIn("border-left: 3px solid transparent;", panel_css)
        self.assertNotIn("app-menu-admin-icon", html + panel_css)
        self.assertIn('-apple-system, BlinkMacSystemFont, "SF Pro Text"', tokens_css)
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("Plus Jakarta Sans", html + tokens_css)
        self.assertNotIn("Outfit", html + tokens_css)


if __name__ == "__main__":
    unittest.main()

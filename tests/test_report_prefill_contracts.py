import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class ReportPrefillFrontendContractTests(unittest.TestCase):
    def test_report_form_prefills_generic_vehicle_report_without_persisting_reporter_pii(self):
        config_js = (ROOT_DIR / "web" / "config.js").read_text(encoding="utf-8")
        reports_js = (ROOT_DIR / "web" / "app" / "reports.js").read_text(encoding="utf-8")
        i18n_pl = (ROOT_DIR / "web" / "i18n" / "pl.js").read_text(encoding="utf-8")

        self.assertNotIn("REPORT_REPORTER_STORAGE_KEY", config_js + reports_js)
        self.assertNotIn("localStorage.setItem", reports_js)
        self.assertIn("localStorage.removeItem('wreckscanner.reportReporter.v1')", reports_js)
        self.assertIn("applyReportAddressDefault", reports_js)
        self.assertIn("ADDRESS_REVERSE_URL", reports_js)
        self.assertIn("modal.report.defaultLocation", reports_js + i18n_pl)
        self.assertIn("modal.report.defaultLocationWithAddress", reports_js + i18n_pl)
        self.assertIn("modal.report.defaultVehicleDescription", reports_js + i18n_pl)
        self.assertIn("Najbliższy adres: {address}", i18n_pl)
        self.assertIn("długotrwale nieużytkowany lub porzucony", i18n_pl)
        self.assertIn("art. 50a ust. 1 Prawa o ruchu drogowym", i18n_pl)


if __name__ == "__main__":
    unittest.main()

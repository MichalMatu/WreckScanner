import re
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class FutureDatabaseContractTests(unittest.TestCase):
    def test_future_database_contract_names_only_target_tables(self):
        doc = (ROOT_DIR / "docs" / "FUTURE_DATABASE.md").read_text(encoding="utf-8")

        for table in ("field_photos", "settings", "privacy_requests"):
            self.assertRegex(doc, rf"`{table}`")

        forbidden_table_lines = re.findall(
            r"^\s*-\s*`(reports|report_packages|public_report_packages|map_crops|report_crops|"
            r"evidence_crops|wrecks|vehicle_cases|cases|evidences)`\s+-\s+",
            doc,
            flags=re.M,
        )
        self.assertEqual(
            set(forbidden_table_lines),
            {
                "reports",
                "report_packages",
                "public_report_packages",
                "map_crops",
                "report_crops",
                "evidence_crops",
                "wrecks",
                "vehicle_cases",
                "cases",
                "evidences",
            },
        )

        self.assertIn("Nie importuj `prywatne_zgloszenia/`", doc)
        self.assertIn("Nie importuj `evidence/report_*`", doc)
        self.assertIn("Nie importuj dawnych katalogów archiwalnych teczek pojazdów", doc)
        self.assertIn("Raportowanie ma działać przez listę `field_photo.id`", doc)


if __name__ == "__main__":
    unittest.main()

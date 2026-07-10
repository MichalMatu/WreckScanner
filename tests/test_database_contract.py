import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class DatabaseContractTests(unittest.TestCase):
    def test_database_document_describes_current_sqlite_contract(self):
        doc = (ROOT_DIR / "docs" / "DATABASE.md").read_text(encoding="utf-8")

        self.assertIn("produkcyjny model SQLite", doc)
        self.assertIn("Aktywnym zrodlem prawdy jest `wreckscanner.sqlite3`", doc)
        self.assertIn("database/migrations/", doc)
        self.assertIn("`schema_migrations`", doc)
        self.assertNotIn("przyszlej migracji", doc.lower())
        self.assertFalse((ROOT_DIR / "docs" / "FUTURE_DATABASE.md").exists())

        for table in ("field_photos", "settings", "privacy_requests"):
            self.assertIn(f"`{table}`", doc)

        for forbidden in (
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
        ):
            self.assertIn(f"`{forbidden}`", doc)

    def test_database_document_separates_runtime_validation_from_legacy_import(self):
        doc = (ROOT_DIR / "docs" / "DATABASE.md").read_text(encoding="utf-8")

        self.assertIn("scripts/migrate_json_to_db.py --validate-only", doc)
        self.assertIn("`PRAGMA quick_check`", doc)
        self.assertIn("`PRAGMA foreign_key_check`", doc)
        self.assertIn("zgodnosc `schema_migrations`", doc)
        self.assertIn("--migrate-legacy-json", doc)
        self.assertIn("SQLite pozostaje jedynym zrodlem prawdy", doc)


if __name__ == "__main__":
    unittest.main()

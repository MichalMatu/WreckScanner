import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT_DIR = Path(__file__).resolve().parent.parent
MIGRATION_PATH = ROOT_DIR / "database" / "migrations" / "001_initial.sql"

ALLOWED_TABLES = {"schema_migrations", "field_photos", "settings", "privacy_requests"}
FORBIDDEN_TABLES = {
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
}


class DatabaseSchemaTests(unittest.TestCase):
    def _migrated_connection(self) -> sqlite3.Connection:
        sql = MIGRATION_PATH.read_text(encoding="utf-8")
        tempdir = TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        db_path = Path(tempdir.name) / "wreckscanner.sqlite3"
        connection = sqlite3.connect(db_path)
        self.addCleanup(connection.close)
        connection.executescript(sql)
        return connection

    def test_initial_migration_uses_sqlite_wal(self):
        sql = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn("PRAGMA journal_mode = WAL;", sql)
        self.assertIn("PRAGMA synchronous = NORMAL;", sql)

        connection = self._migrated_connection()
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

        self.assertEqual(journal_mode.lower(), "wal")

    def test_initial_migration_creates_only_clean_domain_tables(self):
        connection = self._migrated_connection()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }

        self.assertEqual(tables, ALLOWED_TABLES)
        self.assertTrue(FORBIDDEN_TABLES.isdisjoint(tables))

    def test_initial_migration_keeps_reports_and_crops_out_of_schema(self):
        sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

        for forbidden in FORBIDDEN_TABLES:
            self.assertNotIn(f"create table {forbidden}", sql)
            self.assertNotIn(f"create table if not exists {forbidden}", sql)

    def test_field_photo_schema_keeps_files_on_disk_and_tokens_hashed(self):
        connection = self._migrated_connection()
        columns = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(field_photos)")}

        for column in (
            "private_original_file",
            "public_image_file",
            "public_thumb_file",
            "exif_json",
            "submitted_at",
            "owner_redactions_updated_at",
        ):
            self.assertIn(column, columns)
        self.assertIn("edit_token_salt", columns)
        self.assertIn("edit_token_hash", columns)
        self.assertNotIn("edit_token", columns)
        self.assertNotIn("report_file", columns)
        self.assertNotIn("crop_file", columns)


if __name__ == "__main__":
    unittest.main()

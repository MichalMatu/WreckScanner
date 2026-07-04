import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class DocumentationContractTests(unittest.TestCase):
    def test_readme_links_only_essential_docs(self):
        readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")

        self.assertIn("Aktualne wydanie: `v2.0`", readme)
        self.assertIn("Status projektu: wersja utrzymaniowa.", readme)
        self.assertIn("docs/START.md", readme)
        self.assertIn("docs/CURRENT_MODEL.md", readme)
        self.assertIn("docs/BACKUP.md", readme)
        self.assertNotIn("docs/AUDIT.md", readme)
        self.assertNotIn("docs/README.en.md", readme)
        self.assertNotIn("RUNTIME_SMOKE", readme)
        self.assertNotIn("ROADMAP", readme.upper())

    def test_start_doc_has_runtime_admin_and_smoke_basics(self):
        doc = (ROOT_DIR / "docs" / "START.md").read_text(encoding="utf-8")

        self.assertIn("./.venv/bin/python server.py", doc)
        self.assertIn("make restart", doc)
        self.assertIn("WRECKSCANNER_ADMIN_PASSWORD", doc)
        self.assertIn("ma pierwszenstwo przed plikiem `.admin_password`", doc)
        self.assertIn("scripts/check.sh", doc)
        self.assertIn("make smoke", doc)
        self.assertIn("BACKUP.md", doc)

    def test_current_model_doc_names_active_flow_and_retired_artifact_audit(self):
        doc = (ROOT_DIR / "docs" / "CURRENT_MODEL.md").read_text(encoding="utf-8")

        self.assertIn("`wreckscanner.sqlite3` - aktywny stan aplikacji", doc)
        self.assertIn("`zdjecia_terenowe/` - publiczne pliki zdjec terenowych", doc)
        self.assertIn("Kazde zdjecie terenowe musi miec jawne `issue_type`", doc)
        self.assertIn("`POST /api/field-photo-reports/report-package`", doc)
        self.assertIn("Raporty, cropy mapy i paczki ZIP/PDF nie sa zapisywane w DB.", doc)
        self.assertIn("Nie ma publicznego ani administracyjnego API `/api/wrecks`.", doc)
        self.assertIn("test ! -e zidentyfikowane_wraki", doc)
        self.assertIn("scripts/migrate_json_to_db.py --validate-only", doc)
        self.assertIn("scripts/check.sh", doc)

    def test_release_candidate_doc_freezes_baseline_and_next_goal(self):
        doc = (ROOT_DIR / "docs" / "RELEASE_CANDIDATE.md").read_text(encoding="utf-8")

        self.assertIn("restic snapshot: `4aaaca53`", doc)
        self.assertIn("restic snapshot po migracji DB: `05c2b91c`", doc)
        self.assertIn("restic snapshot po przepieciu runtime na DB: `08af6d00`", doc)
        self.assertIn("zdjecia terenowe: `270`", doc)
        self.assertIn("typy zdjec: `vehicle=240`, `infrastructure=29`, `smoke=1`", doc)
        self.assertIn("zgloszenia prywatnosci: `0`", doc)
        self.assertIn("Kontrakt bazy: SQLite/WAL", doc)
        self.assertIn("Migracja JSON -> DB", doc)
        self.assertIn("scripts/migrate_json_to_db.py --validate-only", doc)
        self.assertIn("field_photos=270", doc)
        self.assertIn("missing_paths=0", doc)
        self.assertIn("tag `v1.0.0-rc1`", doc)

    def test_removed_development_docs_stay_removed(self):
        removed = (
            "ADMIN_PASSWORD_ROTATION.md",
            "AUDIT.md",
            "COMMERCIAL_GRADE_GOAL_PROMPT.md",
            "GEOTIFF_RUNBOOK.md",
            "PHOTO_UPLOAD_RUNBOOK.md",
            "README.en.md",
            "RUNTIME_SMOKE.md",
            "claudflare.md",
            "todo.md",
        )

        for name in removed:
            self.assertFalse((ROOT_DIR / "docs" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

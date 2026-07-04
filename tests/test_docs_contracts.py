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
        self.assertIn("docs/DEPLOY.md", readme)
        self.assertIn("OC/UFG", readme)
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
        self.assertIn("make e2e-report", doc)
        self.assertIn("statusem OC/UFG", doc)
        self.assertIn("BACKUP.md", doc)
        self.assertIn("DEPLOY.md", doc)

    def test_deploy_doc_has_production_secret_and_verification_checklist(self):
        doc = (ROOT_DIR / "docs" / "DEPLOY.md").read_text(encoding="utf-8")

        self.assertIn("WRECKSCANNER_ADMIN_PASSWORD", doc)
        self.assertIn("WRECKSCANNER_ADMIN_SESSION_SECRET", doc)
        self.assertIn("WRECKSCANNER_CORS_ALLOWED_ORIGINS", doc)
        self.assertIn("systemctl enable --now wreckscanner.service", doc)
        self.assertIn("./scripts/check.sh", doc)
        self.assertIn("scripts/backup_data.py run", doc)
        self.assertIn("make smoke", doc)
        self.assertIn("make e2e-report", doc)
        self.assertIn("Rollback", doc)

    def test_backup_doc_has_restore_validation_commands(self):
        doc = (ROOT_DIR / "docs" / "BACKUP.md").read_text(encoding="utf-8")

        self.assertIn("restic restore latest --target /tmp/wreckscanner-restore-test", doc)
        self.assertIn("scripts/diagnose_data.py --strict", doc)
        self.assertIn("--field-photos-dir /tmp/wreckscanner-restore-test/zdjecia_terenowe", doc)
        self.assertIn("scripts/migrate_json_to_db.py", doc)
        self.assertIn("--validate-only", doc)

    def test_current_model_doc_names_active_flow_and_retired_artifact_audit(self):
        doc = (ROOT_DIR / "docs" / "CURRENT_MODEL.md").read_text(encoding="utf-8")

        self.assertIn("`wreckscanner.sqlite3` - aktywny stan aplikacji", doc)
        self.assertIn("`zdjecia_terenowe/` - publiczne pliki zdjec terenowych", doc)
        self.assertIn("Kazde zdjecie terenowe musi miec jawne `issue_type`", doc)
        self.assertIn("`vehicle_insurance_status`", doc)
        self.assertIn("Aplikacja nie pobiera danych z UFG automatycznie", doc)
        self.assertIn("Zmiana OC/UFG w panelu admina aktualizuje wszystkie zdjecia pojazdu", doc)
        self.assertIn("`zgloszenie.txt`, `raport.html` i PDF", doc)
        self.assertIn("`POST /api/field-photo-reports/report-package`", doc)
        self.assertIn("Raporty, cropy mapy i paczki ZIP/PDF nie sa zapisywane w DB ani w stalym", doc)
        self.assertIn("Nie ma publicznego ani administracyjnego API `/api/wrecks`.", doc)
        self.assertIn("test ! -e zidentyfikowane_wraki", doc)
        self.assertIn("test ! -e prywatne_zgloszenia", doc)
        self.assertIn("scripts/migrate_json_to_db.py --validate-only", doc)
        self.assertIn("scripts/check.sh", doc)

    def test_release_candidate_archive_stays_removed(self):
        self.assertFalse((ROOT_DIR / "docs" / "RELEASE_CANDIDATE.md").exists())

    def test_removed_development_docs_stay_removed(self):
        removed = (
            "ADMIN_PASSWORD_ROTATION.md",
            "AUDIT.md",
            "COMMERCIAL_GRADE_GOAL_PROMPT.md",
            "GEOTIFF_RUNBOOK.md",
            "PHOTO_UPLOAD_RUNBOOK.md",
            "README.en.md",
            "RELEASE_CANDIDATE.md",
            "RUNTIME_SMOKE.md",
            "claudflare.md",
            "todo.md",
        )

        for name in removed:
            self.assertFalse((ROOT_DIR / "docs" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

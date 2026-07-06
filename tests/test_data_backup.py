import json
import os
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from core.data_backup import (
    ResticOptions,
    restic_check,
    restic_forget,
    restic_init,
    run_backup,
)
from core.database import apply_migrations, connect_database
from core.field_photos import save_field_photo_record
from core.zip_backup import create_zip_backup, restore_zip_backup

ROOT_DIR = Path(__file__).resolve().parent.parent


class RecordingRunner:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls = []

    def __call__(self, command, *, cwd, env, check):
        self.calls.append({"command": command, "cwd": Path(cwd), "env": env, "check": check})
        return subprocess.CompletedProcess(command, self.returncode)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def prepare_root(root: Path) -> Path:
    (root / "zdjecia_terenowe").mkdir()
    (root / "prywatne_zdjecia").mkdir()
    (root / "zgloszenia_prywatnosci").mkdir()
    write_json(root / "settings.json", {"enhancement": {"enabled": True}})
    password_file = root / ".restic_password"
    password_file.write_text("secret\n", encoding="utf-8")
    return password_file


def create_valid_database(root: Path) -> None:
    connection = connect_database(root / "wreckscanner.sqlite3")
    try:
        apply_migrations(connection)
    finally:
        connection.close()


def field_photo_record(photo_id: str = "photo_20260604T200730Z_37885295") -> dict:
    return {
        "id": photo_id,
        "created_at": "2026-06-04T20:07:30Z",
        "original_filename": "teren.jpg",
        "content_type": "image/jpeg",
        "format": "JPEG",
        "size_bytes": 123,
        "image_width": 48,
        "image_height": 32,
        "issue_type": "vehicle",
        "lat": 51.1,
        "lon": 17.2,
        "coordinate_source": "map",
        "private_original_file": f"field_photos/{photo_id}/missing.jpg",
        "public_review_status": "pending",
        "redactions": [],
        "links": {},
    }


def fake_restic(path: Path) -> Path:
    script = path / "fake_restic.py"
    script.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

payload = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "repo": os.environ.get("RESTIC_REPOSITORY"),
    "password_file": os.environ.get("RESTIC_PASSWORD_FILE"),
}
log = Path(os.environ["FAKE_RESTIC_LOG"])
log.write_text(json.dumps(payload), encoding="utf-8")
sys.exit(0)
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


class DataBackupTests(unittest.TestCase):
    def test_run_backup_writes_diagnostics_and_calls_restic_with_default_paths(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            runner = RecordingRunner()
            options = ResticOptions(
                root_dir=root, restic_bin="restic", repository=str(root / "repo"), password_file=password_file
            )

            result = run_backup(options=options, check_images=False, runner=runner)

            self.assertEqual(result.status, "ok")
            self.assertEqual(result.diagnostics_status, "ok")
            self.assertTrue((root / "analiza" / "data_diagnostics.json").exists())
            self.assertEqual(len(runner.calls), 1)
            command = runner.calls[0]["command"]
            self.assertEqual(command[:2], ["restic", "backup"])
            self.assertIn("--tag", command)
            self.assertIn("wreckscanner", command)
            self.assertIn("zdjecia_terenowe", command)
            self.assertIn("prywatne_zdjecia", command)
            self.assertIn("zgloszenia_prywatnosci", command)
            self.assertIn("settings.json", command)
            self.assertIn("analiza/data_diagnostics.json", command)
            self.assertNotIn(".admin_password", command)
            self.assertEqual(runner.calls[0]["env"]["RESTIC_REPOSITORY"], str(root / "repo"))
            self.assertEqual(runner.calls[0]["env"]["RESTIC_PASSWORD_FILE"], str(password_file))
            self.assertEqual(runner.calls[0]["env"]["RESTIC_CACHE_DIR"], str(root / ".cache" / "restic"))

    def test_run_backup_can_include_admin_password_and_extra_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            (root / ".admin_password").write_text("admin-secret\n", encoding="utf-8")
            write_json(root / "custom.json", {"ok": True})
            runner = RecordingRunner()
            options = ResticOptions(
                root_dir=root, restic_bin="restic", repository=str(root / "repo"), password_file=password_file
            )

            result = run_backup(
                options=options,
                include_admin_password=True,
                extra_paths=[Path("custom.json")],
                check_images=False,
                runner=runner,
            )

            self.assertEqual(result.status, "ok")
            command = runner.calls[0]["command"]
            self.assertIn(".admin_password", command)
            self.assertIn("custom.json", command)

    def test_run_backup_includes_database_files_when_present(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            create_valid_database(root)
            (root / "wreckscanner.sqlite3-wal").write_bytes(b"wal")
            (root / "wreckscanner.sqlite3-shm").write_bytes(b"shm")
            runner = RecordingRunner()
            options = ResticOptions(
                root_dir=root, restic_bin="restic", repository=str(root / "repo"), password_file=password_file
            )

            result = run_backup(options=options, check_images=False, runner=runner)

            self.assertEqual(result.status, "ok")
            command = runner.calls[0]["command"]
            self.assertIn("wreckscanner.sqlite3", command)

    def test_run_backup_blocks_when_diagnostics_has_errors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            save_field_photo_record(field_photo_record(), root / "zdjecia_terenowe")
            runner = RecordingRunner()
            options = ResticOptions(
                root_dir=root, restic_bin="restic", repository=str(root / "repo"), password_file=password_file
            )

            result = run_backup(options=options, check_images=False, runner=runner)

            self.assertEqual(result.status, "blocked")
            self.assertEqual(result.diagnostics_status, "error")
            self.assertIn("błędy", result.message)
            self.assertEqual(runner.calls, [])

    def test_run_backup_strict_blocks_warnings(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            (root / "zdjecia_terenowe" / "orphan.bin").write_bytes(b"orphan")
            runner = RecordingRunner()
            options = ResticOptions(
                root_dir=root, restic_bin="restic", repository=str(root / "repo"), password_file=password_file
            )

            result = run_backup(options=options, strict=True, check_images=False, runner=runner)

            self.assertEqual(result.status, "blocked")
            self.assertEqual(result.diagnostics_status, "warning")
            self.assertEqual(runner.calls, [])

    def test_restic_helper_commands_use_repository_and_password_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            options = ResticOptions(root_dir=root, restic_bin="restic", repository="repo", password_file=password_file)
            runner = RecordingRunner()

            self.assertEqual(restic_init(options, runner=runner).command, ["restic", "init"])
            self.assertEqual(restic_check(options, runner=runner).command, ["restic", "check"])
            forget = restic_forget(
                options,
                keep_daily=7,
                keep_weekly=4,
                keep_monthly=2,
                prune=True,
                runner=runner,
            )

            self.assertIn("--keep-daily", forget.command)
            self.assertIn("7", forget.command)
            self.assertIn("--prune", forget.command)
            self.assertEqual(runner.calls[0]["env"]["RESTIC_REPOSITORY"], "repo")

    def test_backup_data_cli_runs_fake_restic_end_to_end(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            password_file = prepare_root(root)
            restic_bin = fake_restic(root)
            restic_log = root / "restic-log.json"
            env = os.environ.copy()
            env["FAKE_RESTIC_LOG"] = str(restic_log)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "backup_data.py"),
                    "run",
                    "--root-dir",
                    str(root),
                    "--restic-bin",
                    str(restic_bin),
                    "--repo",
                    str(root / "repo"),
                    "--password-file",
                    str(password_file),
                    "--no-image-check",
                    "--dry-run",
                ],
                cwd=ROOT_DIR,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Diagnostyka zapisana", result.stdout)
            payload = json.loads(restic_log.read_text(encoding="utf-8"))
            self.assertEqual(payload["argv"][0], "backup")
            self.assertIn("--dry-run", payload["argv"])
            self.assertNotIn("zidentyfikowane_wraki", payload["argv"])
            self.assertIn("prywatne_zdjecia", payload["argv"])
            self.assertIn("zgloszenia_prywatnosci", payload["argv"])
            self.assertEqual(payload["repo"], str(root / "repo"))
            self.assertEqual(payload["password_file"], str(password_file))

    def test_create_zip_backup_includes_database_photos_settings_and_secrets(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_root(root)
            create_valid_database(root)
            (root / ".admin_password").write_text("admin-secret\n", encoding="utf-8")
            (root / "zdjecia_terenowe" / "public.txt").write_text("public photo placeholder", encoding="utf-8")
            (root / "prywatne_zdjecia" / "private.txt").write_text("private photo placeholder", encoding="utf-8")

            result = create_zip_backup(root_dir=root, check_images=False)

            self.assertEqual(result.status, "ok")
            self.assertIsNotNone(result.archive_path)
            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())
                self.assertIn("wreckscanner.sqlite3", names)
                self.assertIn("zdjecia_terenowe/public.txt", names)
                self.assertIn("prywatne_zdjecia/private.txt", names)
                self.assertIn("settings.json", names)
                self.assertIn(".admin_password", names)
                self.assertIn(".restic_password", names)
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))

            self.assertEqual(manifest["format"], "wreckscanner-data-snapshot-v1")
            self.assertTrue(manifest["secrets_included"])
            self.assertIn(".admin_password", manifest["secret_entries"])
            self.assertIn(".restic_password", manifest["secret_entries"])

    def test_restore_zip_backup_replaces_snapshot_paths_and_keeps_safety_copy(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_root(root)
            create_valid_database(root)
            (root / ".admin_password").write_text("original-admin\n", encoding="utf-8")
            (root / "zdjecia_terenowe" / "snapshot.txt").write_text("snapshot public", encoding="utf-8")
            (root / "prywatne_zdjecia" / "snapshot.txt").write_text("snapshot private", encoding="utf-8")
            (root / "settings.json").write_text('{"version":"snapshot"}\n', encoding="utf-8")
            backup = create_zip_backup(root_dir=root, check_images=False)

            self.assertEqual(backup.status, "ok")
            (root / ".admin_password").write_text("changed-admin\n", encoding="utf-8")
            (root / "zdjecia_terenowe" / "changed.txt").write_text("changed public", encoding="utf-8")
            (root / "prywatne_zdjecia" / "changed.txt").write_text("changed private", encoding="utf-8")
            (root / "settings.json").write_text('{"version":"changed"}\n', encoding="utf-8")

            result = restore_zip_backup(root_dir=root, archive_path=backup.archive_path)

            self.assertEqual(result.status, "ok")
            self.assertIsNotNone(result.safety_path)
            self.assertEqual((root / ".admin_password").read_text(encoding="utf-8"), "original-admin\n")
            self.assertTrue((root / "zdjecia_terenowe" / "snapshot.txt").exists())
            self.assertTrue((root / "prywatne_zdjecia" / "snapshot.txt").exists())
            self.assertFalse((root / "zdjecia_terenowe" / "changed.txt").exists())
            self.assertFalse((root / "prywatne_zdjecia" / "changed.txt").exists())
            self.assertEqual((root / "settings.json").read_text(encoding="utf-8"), '{"version":"snapshot"}\n')
            self.assertTrue((result.safety_path / "settings.json").exists())
            self.assertTrue((result.safety_path / "zdjecia_terenowe" / "changed.txt").exists())


if __name__ == "__main__":
    unittest.main()

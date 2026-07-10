import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


class ToolingContractTests(unittest.TestCase):
    def test_opencv_uses_the_published_python_distribution_pin(self):
        requirements = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("opencv-python==5.0.0.93", requirements.splitlines())
        self.assertNotIn("opencv-python==5.0.0", requirements.splitlines())

    def test_numpy_pin_covers_every_supported_python_runtime(self):
        requirements = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn('numpy==2.3.5; python_version < "3.12"', requirements.splitlines())
        self.assertIn('numpy==2.5.0; python_version >= "3.12"', requirements.splitlines())
        self.assertNotIn("numpy==2.5.0", requirements.splitlines())

    def test_make_lint_delegates_to_recursive_frontend_linter(self):
        makefile = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")
        lint_target = makefile.split("lint:\n", 1)[1].split("\nsmoke:", 1)[0]

        self.assertIn("npm run lint:web", lint_target)
        self.assertNotIn("eslint web/*.js", lint_target)
        self.assertIn("npm jest wymagany", lint_target)

    def test_ci_covers_supported_python_runtime_endpoints(self):
        workflow = (ROOT_DIR / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")

        self.assertIn("fail-fast: false", workflow)
        self.assertIn('python-version: ["3.11", "3.13"]', workflow)
        self.assertIn("python-version: ${{ matrix.python-version }}", workflow)

    def test_check_script_annotates_the_exact_failing_ci_command(self):
        check_script = (ROOT_DIR / "scripts" / "check.sh").read_text(encoding="utf-8")

        self.assertIn('[[ "${GITHUB_ACTIONS:-}" == "true" ]]', check_script)
        self.assertIn("::error title=check.sh command failed::", check_script)
        self.assertIn('report_failure "$status" "$@"', check_script)

    def test_ci_actions_are_pinned_to_immutable_commit_shas(self):
        workflow = (ROOT_DIR / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")

        self.assertIn("actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4", workflow)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5", workflow)
        self.assertIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4", workflow)
        action_lines = [line.strip() for line in workflow.splitlines() if "uses: actions/" in line]
        self.assertEqual(len(action_lines), 3)
        for line in action_lines:
            self.assertRegex(line, r"uses: actions/[^@]+@[0-9a-f]{40}(?:\s+#\s+v\d+)?$")

    def test_make_uses_readiness_to_admit_traffic(self):
        makefile = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")

        self.assertIn("/api/health/live", makefile)
        self.assertIn("/api/health/ready", makefile)
        self.assertIn('curl -fsS "$(SERVER_READY_URL)"', makefile)
        self.assertIn("curl jest wymagany do sprawdzenia readiness", makefile)
        self.assertNotIn("Sprawdz watcher albo uruchom tymczasowo", makefile)

    def test_autostart_never_falls_back_to_a_manual_server(self):
        makefile = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")
        autostart = makefile.split("autostart-start:\n", 1)[1].split("\nautostart-status:", 1)[0]

        self.assertIn("$(MAKE) SERVER_WAIT_SECONDS=$(SERVER_AUTOSTART_WAIT_SECONDS) wait-server", autostart)
        self.assertIn("Reczna instancja nie zostala uruchomiona", autostart)
        self.assertNotIn("pgrep", autostart)
        self.assertNotIn("nohup", autostart)
        self.assertNotIn("server.pid", makefile)
        self.assertNotIn("$(MAKE) autostart-start || true", makefile)

    def test_make_exposes_incremental_restic_backup_and_rotation(self):
        makefile = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")

        self.assertIn("backup-restic:", makefile)
        self.assertIn("prune-restic:", makefile)
        self.assertIn("check-restic:", makefile)
        self.assertIn("list-restic:", makefile)
        self.assertIn("--keep-daily 0 --keep-weekly 8 --keep-monthly 6 --prune", makefile)
        self.assertIn("scripts/backup_data.py run", makefile)
        self.assertIn("--strict", makefile)

    def test_user_backup_timer_runs_backup_rotation_and_check(self):
        unit_dir = ROOT_DIR / "deploy" / "systemd"
        service = (unit_dir / "wreckscanner-backup.service").read_text(encoding="utf-8")
        timer = (unit_dir / "wreckscanner-backup.timer").read_text(encoding="utf-8")

        self.assertIn("Type=oneshot", service)
        self.assertIn("NoNewPrivileges=true", service)
        self.assertIn("ExecStart=/usr/bin/make backup-restic", service)
        self.assertIn("ExecStart=/usr/bin/make prune-restic", service)
        self.assertIn("ExecStart=/usr/bin/make check-restic", service)
        self.assertIn("OnCalendar=Sun *-*-* 04:00:00", timer)
        self.assertIn("Persistent=true", timer)
        self.assertIn("RandomizedDelaySec=30m", timer)


if __name__ == "__main__":
    unittest.main()

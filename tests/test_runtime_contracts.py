import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from core.runtime import (
    PYTHON_IO_ENCODING,
    TEXT_ENCODING,
    TEXT_ERRORS,
    configure_process_encoding,
    subprocess_text_kwargs,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


class FakeTextStream:
    def __init__(self):
        self.reconfigure_calls = []

    def reconfigure(self, **kwargs):
        self.reconfigure_calls.append(kwargs)


class RuntimeEncodingContractTests(unittest.TestCase):
    def test_configure_process_encoding_forces_safe_text_streams(self):
        stdout = FakeTextStream()
        stderr = FakeTextStream()

        with (
            patch.object(sys, "stdout", stdout),
            patch.object(sys, "stderr", stderr),
            patch.dict(os.environ, {"PYTHONIOENCODING": "latin-1"}, clear=True),
        ):
            configure_process_encoding()

            self.assertEqual(os.environ["PYTHONIOENCODING"], PYTHON_IO_ENCODING)

        expected = {"encoding": TEXT_ENCODING, "errors": TEXT_ERRORS}
        self.assertEqual(stdout.reconfigure_calls, [expected])
        self.assertEqual(stderr.reconfigure_calls, [expected])

    def test_subprocess_text_kwargs_decode_utf8_with_replacement(self):
        self.assertEqual(
            subprocess_text_kwargs(),
            {"encoding": TEXT_ENCODING, "errors": TEXT_ERRORS},
        )

    def test_makefile_exposes_operational_commands(self):
        makefile = (ROOT_DIR / "Makefile").read_text(encoding="utf-8")

        for target in (
            "start:",
            "stop:",
            "restart:",
            "wait-server:",
            "require-local-watcher:",
            "autostart-start: require-local-watcher",
            "autostart-stop: require-local-watcher",
            "autostart-status:",
            "serwerstart:",
            "serwerstop:",
            "status:",
            "logs:",
            "check:",
            "test:",
            "lint:",
            "smoke:",
        ):
            self.assertIn(target, makefile)
        self.assertIn(
            "SERVER_PATTERN := [p]ython[^[:space:]]*[[:space:]].*$(CURDIR)/server\\.py([[:space:]]|$$)",
            makefile,
        )
        self.assertIn("pgrep -af '$(SERVER_PATTERN)'", makefile)
        self.assertIn('kill -0 "$$pid"', makefile)
        self.assertIn("nie uruchamia procesu", makefile)
        self.assertIn("AUTOSTART_DISABLED_FILE ?= .dev/server.autostart.disabled", makefile)
        self.assertIn("SYSTEMD_UNIT ?= wreckscanner.service", makefile)
        self.assertIn("SYSTEMD_WORKING_DIRECTORY :=", makefile)
        self.assertIn("SYSTEMD_MANAGED ?=", makefile)
        self.assertIn("journalctl", makefile.lower())
        self.assertIn('exit "$$status"', makefile)
        self.assertIn("trap finish EXIT", makefile)
        self.assertNotIn("nohup", makefile)
        self.assertNotIn("SERVER_PID_FILE", makefile)
        self.assertNotIn("\nautostart:\n", makefile)
        self.assertNotIn("\nbackup-db:", makefile)
        self.assertNotIn("\nrestore-db:", makefile)
        self.assertIn("Reczna instancja nie zostala uruchomiona", makefile)
        self.assertIn("$(SUBMAKE) wait-server", makefile)
        self.assertIn("error: npm jest wymagany do lintowania calego frontendu", makefile)
        self.assertIn("npm run lint:web", makefile)
        self.assertNotIn("eslint web/*.js", makefile)
        self.assertIn("SERVER_LIVE_URL := $(SERVER_URL)/api/health/live", makefile)
        self.assertIn("SERVER_READY_URL := $(SERVER_URL)/api/health/ready", makefile)
        self.assertIn("./scripts/check.sh", makefile)
        self.assertIn('scripts/smoke_runtime.py --base-url "$(SERVER_URL)"', makefile)

    def test_github_check_workflow_installs_frontend_dependencies(self):
        workflow = (ROOT_DIR / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")

        self.assertIn("uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4", workflow)
        self.assertIn('node-version: "22"', workflow)
        self.assertIn('cache: "npm"', workflow)
        self.assertIn("run: npm ci", workflow)
        self.assertLess(workflow.index("run: npm ci"), workflow.index("run: scripts/check.sh"))

    def test_e2e_captures_required_viewports_languages_and_zoom(self):
        script = (ROOT_DIR / "scripts" / "e2e_field_photo_report.py").read_text(encoding="utf-8")

        for viewport, size, language in (
            ("desktop-pl", "size=(1366, 900)", 'language="pl"'),
            ("tablet-en", "size=(768, 1024)", 'language="en"'),
            ("mobile-pl", "size=(390, 844)", 'language="pl"'),
        ):
            block = script.split(f'viewport="{viewport}"', 1)[1][:600]
            self.assertIn(size, block)
            self.assertIn(language, block)
        zoom_block = script.split('viewport="zoom-200-en"', 1)[1][:600]
        self.assertIn("size=(683, 450)", zoom_block)
        self.assertIn("device_scale_factor=2.0", zoom_block)

    def test_server_entrypoint_respects_autostart_disable_file(self):
        entrypoint = (ROOT_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn(
            'AUTOSTART_DISABLED_FILE = Path(__file__).resolve().parent / ".dev" / "server.autostart.disabled"',
            entrypoint,
        )
        self.assertIn("if AUTOSTART_DISABLED_FILE.exists():", entrypoint)
        self.assertIn("autostart wylaczony", entrypoint)


if __name__ == "__main__":
    unittest.main()

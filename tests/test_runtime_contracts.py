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
            "autostart:",
            "autostart-start:",
            "autostart-stop:",
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
        self.assertIn("make nie uruchamia drugiej kopii serwera", makefile)
        self.assertIn("AUTOSTART_DISABLED_FILE ?= .dev/server.autostart.disabled", makefile)
        self.assertIn('nohup "$(PYTHON)" "$(CURDIR)/server.py"', makefile)
        self.assertIn("$(MAKE) wait-server", makefile)
        self.assertIn("skip: npm/eslint niedostepne, pomijam lint JS", makefile)
        self.assertIn("./scripts/check.sh", makefile)
        self.assertIn('scripts/smoke_runtime.py --base-url "$(SERVER_URL)"', makefile)

    def test_github_check_workflow_installs_frontend_dependencies(self):
        workflow = (ROOT_DIR / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")

        self.assertIn("uses: actions/setup-node@v4", workflow)
        self.assertIn('node-version: "22"', workflow)
        self.assertIn('cache: "npm"', workflow)
        self.assertIn("run: npm ci", workflow)
        self.assertLess(workflow.index("run: npm ci"), workflow.index("run: scripts/check.sh"))

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

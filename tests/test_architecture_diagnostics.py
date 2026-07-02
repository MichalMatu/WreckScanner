import ast
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import diagnose_architecture

ROOT_DIR = Path(__file__).resolve().parent.parent


class ArchitectureDiagnosticsToolAvailabilityTests(unittest.TestCase):
    def test_tool_info_reports_successful_executable_as_available(self):
        completed = subprocess.CompletedProcess(["ruff", "--version"], 0, stdout="ruff 0.15.15\n", stderr="")

        with (
            patch.object(diagnose_architecture, "_tool_executable", return_value="/venv/bin/ruff"),
            patch.object(diagnose_architecture.subprocess, "run", return_value=completed),
        ):
            result = diagnose_architecture.tool_info("ruff", "--version")

        self.assertEqual(result["command"], "ruff")
        self.assertTrue(result["available"])
        self.assertEqual(result["path"], "/venv/bin/ruff")
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["version"], "ruff 0.15.15")
        self.assertNotIn("error", result)

    def test_tool_info_reports_missing_command_without_module_as_unavailable(self):
        with patch.object(diagnose_architecture, "_tool_executable", return_value=None):
            result = diagnose_architecture.tool_info("node", "--version")

        self.assertEqual(result, {"command": "node", "available": False})

    def test_tool_info_reports_failed_python_module_fallback_as_unavailable(self):
        completed = subprocess.CompletedProcess(
            ["/venv/bin/python", "-m", "bandit", "--version"],
            1,
            stdout="",
            stderr="/venv/bin/python: No module named bandit\n",
        )

        with (
            patch.object(diagnose_architecture, "_tool_executable", return_value=None),
            patch.object(diagnose_architecture.sys, "executable", "/venv/bin/python"),
            patch.object(diagnose_architecture.subprocess, "run", return_value=completed),
        ):
            result = diagnose_architecture.tool_info("bandit", "--version", module="bandit")

        self.assertEqual(result["command"], "bandit")
        self.assertFalse(result["available"])
        self.assertEqual(result["path"], "/venv/bin/python -m bandit")
        self.assertEqual(result["returncode"], 1)
        self.assertEqual(result["error"], "/venv/bin/python: No module named bandit")
        self.assertNotIn("version", result)

    def test_tool_info_reports_subprocess_failure_as_unavailable(self):
        with (
            patch.object(diagnose_architecture, "_tool_executable", return_value="/venv/bin/radon"),
            patch.object(diagnose_architecture.subprocess, "run", side_effect=subprocess.TimeoutExpired("radon", 5)),
        ):
            result = diagnose_architecture.tool_info("radon", "--version")

        self.assertEqual(result["command"], "radon")
        self.assertFalse(result["available"])
        self.assertEqual(result["path"], "/venv/bin/radon")
        self.assertIn("timed out", result["error"])

    def test_frontend_module_contract_tests_stay_split(self):
        source = (ROOT_DIR / "tests" / "test_frontend_contracts.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        frontend_class = next(
            node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "FrontendContracts"
        )
        test_lengths = {
            node.name: node.end_lineno - node.lineno + 1
            for node in frontend_class.body
            if isinstance(node, ast.FunctionDef)
        }

        self.assertNotIn("test_frontend_uses_relative_backend_urls_for_tunnel_deployments", test_lengths)
        self.assertNotIn("test_report_package_modal_and_admin_popup_action_exist", test_lengths)
        self.assertNotIn("test_admin_field_photo_upload_layer_exists", test_lengths)
        self.assertNotIn("test_map_layer_toggles_and_manual_wreck_creation_exist", test_lengths)
        self.assertGreaterEqual(len(test_lengths), 3)
        for name, length in test_lengths.items():
            with self.subTest(name=name):
                self.assertLessEqual(length, 130)


if __name__ == "__main__":
    unittest.main()

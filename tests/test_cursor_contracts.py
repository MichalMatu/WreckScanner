from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
STYLE_DIR = ROOT_DIR / "web" / "styles"


class CursorContracts(unittest.TestCase):
    def test_interactive_cursors_use_tokens_and_global_control_contract(self):
        tokens = (STYLE_DIR / "tokens.css").read_text(encoding="utf-8")
        base = (STYLE_DIR / "base.css").read_text(encoding="utf-8")

        self.assertIn("--cursor-action: pointer;", tokens)
        self.assertIn("--cursor-disabled: not-allowed;", tokens)
        self.assertIn("--cursor-busy: wait;", tokens)
        self.assertIn("--cursor-progress: progress;", tokens)
        self.assertIn("--cursor-static: default;", tokens)

        for selector in (
            "a[href]",
            "button:not(:disabled)",
            "label[for]",
            'input[type="range"]:not(:disabled)',
            '[role="tab"]:not([aria-disabled="true"])',
            '[role="menuitem"]:not([aria-disabled="true"])',
        ):
            self.assertIn(selector, base)
        self.assertIn("cursor: var(--cursor-action);", base)
        self.assertIn("cursor: var(--cursor-disabled);", base)

    def test_css_does_not_reintroduce_raw_standard_cursor_values(self):
        raw_cursor = re.compile(r"cursor\s*:\s*(pointer|not-allowed|wait|progress|default)\b")
        offenders: list[str] = []
        for path in sorted(STYLE_DIR.glob("*.css")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if raw_cursor.search(line):
                    offenders.append(f"{path.relative_to(ROOT_DIR)}:{line_number}: {line.strip()}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

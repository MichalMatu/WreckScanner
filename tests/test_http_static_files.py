import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import config
from app.http import static_files


class FakeHandler:
    def __init__(self):
        self.status = None
        self.headers = []
        self.wfile = BytesIO()

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.headers.append((key, value))

    def end_headers(self) -> None:
        return None


class HttpStaticFilesContractTests(unittest.TestCase):
    def test_send_file_can_omit_head_body(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.html"
            path.write_text("<html>ok</html>", encoding="utf-8")
            handler = FakeHandler()

            static_files.send_file(handler, path, "text/html; charset=utf-8", include_body=False)

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.wfile.getvalue(), b"")
        self.assertIn(("Content-Length", "15"), handler.headers)

    def test_translate_path_sanitizes_dot_segments_inside_web_dir(self):
        with TemporaryDirectory() as tmp:
            web_dir = Path(tmp) / "web"
            root_dir = Path(tmp)

            with (
                patch.object(config, "WEB_DIR", web_dir),
                patch.object(config, "ROOT_DIR", root_dir),
                patch.object(config, "ANALYSIS_DIR_NAME", "analiza"),
                patch.object(config, "WRECKS_ROUTE", "wraki"),
            ):
                translated = static_files.translate_path("/../app.js")

        self.assertEqual(translated, str(web_dir / "app.js"))


if __name__ == "__main__":
    unittest.main()

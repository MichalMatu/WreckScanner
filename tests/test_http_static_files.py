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

    def test_send_file_can_set_download_filename(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.zip"
            path.write_bytes(b"zip")
            handler = FakeHandler()

            static_files.send_file(handler, path, "application/zip", download_name="raport_20260702_142516.zip")

        self.assertEqual(handler.status, 200)
        self.assertIn(
            (
                "Content-Disposition",
                "attachment; filename=\"raport_20260702_142516.zip\"; filename*=UTF-8''raport_20260702_142516.zip",
            ),
            handler.headers,
        )

    def test_translate_path_sanitizes_dot_segments_inside_web_dir(self):
        with TemporaryDirectory() as tmp:
            web_dir = Path(tmp) / "web"
            root_dir = Path(tmp)

            with (
                patch.object(config, "WEB_DIR", web_dir),
                patch.object(config, "ROOT_DIR", root_dir),
            ):
                translated = static_files.translate_path("/../app.js")

        self.assertEqual(translated, str(web_dir / "app.js"))

    def test_render_web_template_expands_safe_partials(self):
        with TemporaryDirectory() as tmp:
            web_dir = Path(tmp) / "web"
            (web_dir / "partials").mkdir(parents=True)
            (web_dir / "index.html").write_text(
                "<main>\n<!-- include:partials/body.html -->\n</main>\n",
                encoding="utf-8",
            )
            (web_dir / "partials" / "body.html").write_text("<p>OK</p>\n", encoding="utf-8")

            with patch.object(config, "WEB_DIR", web_dir):
                rendered = static_files.render_web_template("index.html")

        self.assertEqual(rendered, "<main>\n<p>OK</p>\n\n</main>\n")

    def test_render_web_template_rejects_unsafe_partials(self):
        with TemporaryDirectory() as tmp:
            web_dir = Path(tmp) / "web"
            web_dir.mkdir()
            (web_dir / "index.html").write_text("<!-- include:../secret.html -->\n", encoding="utf-8")

            with (
                patch.object(config, "WEB_DIR", web_dir),
                self.assertRaises(FileNotFoundError),
            ):
                static_files.render_web_template("index.html")

    def test_handle_web_page_serves_rendered_index_without_head_body(self):
        with TemporaryDirectory() as tmp:
            web_dir = Path(tmp) / "web"
            (web_dir / "partials").mkdir(parents=True)
            (web_dir / "index.html").write_text(
                "<html>\n<!-- include:partials/app.html -->\n</html>\n",
                encoding="utf-8",
            )
            (web_dir / "partials" / "app.html").write_text("<body>app</body>\n", encoding="utf-8")
            handler = FakeHandler()
            expected_body = b"<html>\n<body>app</body>\n\n</html>\n"

            with patch.object(config, "WEB_DIR", web_dir):
                handled = static_files.handle_web_page(handler, "/privacy", include_body=False)

        self.assertTrue(handled)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.wfile.getvalue(), b"")
        self.assertIn(("Content-Length", str(len(expected_body))), handler.headers)


if __name__ == "__main__":
    unittest.main()

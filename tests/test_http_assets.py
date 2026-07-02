import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.http import assets
from core import config as core_config


class FakeHandler:
    def __init__(self):
        self.status = None
        self.headers = []
        self.wfile = BytesIO()
        self.path = ""

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.headers.append((key, value))

    def end_headers(self) -> None:
        return None


class HttpAssetsTests(unittest.TestCase):
    def test_report_package_download_uses_readable_filename_header(self):
        with TemporaryDirectory() as tmp:
            reports_dir = Path(tmp) / "reports"
            wreck_id = "wreck_51100000_17200000"
            package_id = "report_20260702T142516Z_0b05a053"
            (reports_dir / wreck_id).mkdir(parents=True)
            (reports_dir / wreck_id / f"{package_id}.zip").write_bytes(b"zip")
            handler = FakeHandler()

            with (
                patch.object(core_config, "PRIVATE_REPORTS_DIR", reports_dir),
                patch("app.http.assets.http_admin_session.require_admin", return_value=True),
            ):
                assets.handle_report_package_asset(
                    handler,
                    (wreck_id, package_id, "raport_20260702_142516.zip"),
                )

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.wfile.getvalue(), b"zip")
        self.assertIn(
            (
                "Content-Disposition",
                'attachment; filename="raport_20260702_142516.zip"; filename*=UTF-8\'\'raport_20260702_142516.zip',
            ),
            handler.headers,
        )


if __name__ == "__main__":
    unittest.main()

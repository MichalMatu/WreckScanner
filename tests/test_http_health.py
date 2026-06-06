import json
import unittest
from io import BytesIO
from unittest.mock import patch

from app.http import health


class FakeHandler:
    def __init__(self):
        self.client_address = ("127.0.0.1", 12345)
        self.command = "GET"
        self.headers = {}
        self.path = "/api/health"
        self.response_headers = []
        self.status = None
        self.wfile = BytesIO()

    @property
    def payload(self) -> dict:
        return json.loads(self.wfile.getvalue().decode("utf-8"))

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.response_headers.append((key, value))

    def end_headers(self) -> None:
        return None


class HttpHealthContractTests(unittest.TestCase):
    def test_health_payload_includes_pressure_pipeline_and_wms_cache(self):
        handler = FakeHandler()

        with (
            patch.object(health.pipeline, "system_pressure", return_value={"overloaded": False, "reasons": []}),
            patch.object(health.pipeline, "pipeline_snapshot", return_value={"status": "idle"}),
            patch.object(health.wms_cache, "tile_cache_report", return_value={"count": 2}),
        ):
            health.handle_health(handler)

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.payload["status"], "ok")
        self.assertEqual(handler.payload["pipeline"], {"status": "idle"})
        self.assertEqual(handler.payload["wms_tile_cache"], {"count": 2})


if __name__ == "__main__":
    unittest.main()

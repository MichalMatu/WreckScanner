from __future__ import annotations

import tempfile
import unittest
from io import BytesIO

from PIL import Image

from core.map_crops import fetch_location_crops, save_location_crops


def png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (32, 32), color)
    pixels = image.load()
    for x in range(32):
        for y in range(32):
            delta = 90 if (x + y) % 2 else -30
            pixels[x, y] = (
                max(0, min(255, color[0] + delta)),
                max(0, min(255, color[1] + delta)),
                max(0, min(255, color[2] + delta)),
            )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse:
    status_code = 200

    def __init__(self, content: bytes):
        self.content = content


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        year = url.split("OGC_ortofoto_", 1)[1].split("/", 1)[0]
        return FakeResponse(png_bytes((20, 40, 80) if year == "2024" else (220, 230, 240)))


class MapCropTests(unittest.TestCase):
    def test_fetch_location_crops_downloads_wms_by_location_without_scan_metadata(self):
        session = FakeSession()

        crops, metadata = fetch_location_crops(51.1, 17.2, crop_m=7.5, years=(2024, 2025), session=session)

        self.assertEqual([crop.label for crop in crops], ["2024", "2025"])
        self.assertEqual(metadata["source"], "wroclaw_wms_location_crops")
        self.assertEqual(metadata["years"], [2024, 2025])
        self.assertIn("bbox_4326", metadata)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0][1]["REQUEST"], "GetMap")

    def test_save_location_crops_writes_only_case_evidence_images(self):
        session = FakeSession()
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path

            out = Path(tmp)
            crops, metadata = save_location_crops(51.1, 17.2, out, crop_m=7.5, years=(2024, 2025), session=session)

            self.assertTrue((out / "2024.jpg").exists())
            self.assertTrue((out / "2025.jpg").exists())
            self.assertEqual([crop["label"] for crop in crops], ["2024", "2025"])
            self.assertEqual(metadata["source"], "wroclaw_wms_location_crops")

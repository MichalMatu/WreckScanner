from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

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


def low_contrast_png_bytes() -> bytes:
    image = Image.new("RGB", (32, 32), (80, 84, 92))
    pixels = image.load()
    for x in range(32):
        for y in range(32):
            delta = 2 if (x + y) % 2 else -2
            pixels[x, y] = (80 + delta, 84 + delta, 92 + delta)
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        year = url.split("OGC_ortofoto_", 1)[1].split("/", 1)[0]
        return FakeResponse(png_bytes((20, 40, 80) if year == "2024" else (220, 230, 240)))


class LowContrastSession:
    def get(self, url, *, params, timeout):
        return FakeResponse(low_contrast_png_bytes())


class FlakySession:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        year = url.split("OGC_ortofoto_", 1)[1].split("/", 1)[0]
        self.calls.append(year)
        if self.calls.count(year) == 1:
            return FakeResponse(b"Bad Gateway", status_code=502)
        return FakeResponse(png_bytes((20, 40, 80)))


class MapCropTests(unittest.TestCase):
    def test_fetch_location_crops_downloads_wms_by_location_without_scan_metadata(self):
        session = FakeSession()

        crops, metadata = fetch_location_crops(51.1, 17.2, crop_m=7.5, years=(2024, 2025), session=session)

        self.assertEqual([crop.label for crop in crops], ["2024", "2025"])
        self.assertEqual(metadata["source"], "wroclaw_wms_location_crops")
        self.assertEqual(metadata["requested_years"], [2024, 2025])
        self.assertEqual(metadata["years"], [2024, 2025])
        self.assertEqual(metadata["missing_years"], [])
        self.assertIn("bbox_4326", metadata)
        self.assertIn("bbox_3857", metadata)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0][1]["REQUEST"], "GetMap")
        self.assertEqual(session.calls[0][1]["CRS"], "EPSG:3857")
        self.assertGreater(float(session.calls[0][1]["BBOX"].split(",")[0]), 1_000_000)

    def test_fetch_location_crops_keeps_low_contrast_real_orthophoto(self):
        crops, metadata = fetch_location_crops(51.1, 17.2, crop_m=7.5, years=(2021,), session=LowContrastSession())

        self.assertEqual([crop.label for crop in crops], ["2021"])
        self.assertEqual(metadata["years"], [2021])
        self.assertEqual(metadata["missing_years"], [])

    def test_fetch_location_crops_retries_transient_wms_failure(self):
        session = FlakySession()

        with patch("core.map_crops.time.sleep") as sleep:
            crops, metadata = fetch_location_crops(51.1, 17.2, crop_m=7.5, years=(2024,), session=session)

        self.assertEqual([crop.label for crop in crops], ["2024"])
        self.assertEqual(session.calls, ["2024", "2024"])
        self.assertEqual(metadata["requested_years"], [2024])
        self.assertEqual(metadata["missing_years"], [])
        sleep.assert_called_once()

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

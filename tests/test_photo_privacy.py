import math
import unittest

from core import config
from core.photo_privacy import normalize_redactions


class PhotoPrivacyValidationTests(unittest.TestCase):
    def test_rejects_non_finite_redaction_coordinates(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "współrzędne"):
                normalize_redactions([{"points": [{"x": value, "y": 0}, {"x": 0.5, "y": 0}, {"x": 0.5, "y": 0.5}]}])

    def test_limits_redaction_areas_and_points(self):
        area = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
        with self.assertRaisesRegex(ValueError, "maksymalnie"):
            normalize_redactions([area] * (config.MAX_PHOTO_REDACTIONS + 1))

        points = [{"x": index / 100, "y": (index % 2) / 2} for index in range(config.MAX_REDACTION_POINTS + 1)]
        with self.assertRaisesRegex(ValueError, "maksymalnie"):
            normalize_redactions([{"points": points}])


if __name__ == "__main__":
    unittest.main()

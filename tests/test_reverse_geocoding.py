import unittest
from unittest.mock import patch

from app.http import public_data
from core.reverse_geocoding import normalize_reverse_geocode_result


class ReverseGeocodingTests(unittest.TestCase):
    def test_normalize_reverse_geocode_result_extracts_address_parts(self):
        result = normalize_reverse_geocode_result(
            {
                "lat": "51.087935",
                "lon": "17.044700",
                "display_name": "Komuny Paryskiej 73, Przedmieście Oławskie, Wrocław",
                "address": {
                    "road": "Komuny Paryskiej",
                    "house_number": "73",
                    "postcode": "50-452",
                    "city": "Wrocław",
                    "suburb": "Przedmieście Oławskie",
                },
            },
            query_lat=51.087930,
            query_lon=17.044685,
        )

        self.assertEqual(result["formatted"], "Komuny Paryskiej 73, 50-452, Wrocław")
        self.assertEqual(result["road"], "Komuny Paryskiej")
        self.assertEqual(result["house_number"], "73")
        self.assertEqual(result["district"], "Przedmieście Oławskie")
        self.assertEqual(result["source"], "nominatim")
        self.assertIsInstance(result["distance_m"], int)

    def test_normalize_reverse_geocode_result_requires_some_address_label(self):
        with self.assertRaisesRegex(LookupError, "adresu"):
            normalize_reverse_geocode_result({}, query_lat=51.0, query_lon=17.0)

    def test_lookup_nearest_address_uses_rounded_coordinate_cache(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "lat": "51.087930",
                    "lon": "17.044685",
                    "display_name": "Komuny Paryskiej 73, Wrocław",
                    "address": {"road": "Komuny Paryskiej", "house_number": "73", "city": "Wrocław"},
                }

        class FakeSession:
            calls = 0

            def get(self, *args, **kwargs):
                self.calls += 1
                return FakeResponse()

        session = FakeSession()
        public_data._lookup_nearest_address_cached.cache_clear()
        try:
            with patch.object(public_data.map_downloads, "get_http_session", return_value=session):
                first = public_data.lookup_nearest_address(51.0879301, 17.0446851)
                second = public_data.lookup_nearest_address(51.0879302, 17.0446852)

            self.assertEqual(first["formatted"], "Komuny Paryskiej 73, Wrocław")
            self.assertEqual(second["formatted"], first["formatted"])
            self.assertEqual(session.calls, 1)
        finally:
            public_data._lookup_nearest_address_cached.cache_clear()


if __name__ == "__main__":
    unittest.main()

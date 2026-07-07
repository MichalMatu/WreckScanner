import unittest
from unittest.mock import patch

from app.http import public_data
from core.prg_addresses import parse_prg_address_features, prg_address_wfs_params
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
        self.assertEqual(result["source_label"], "OpenStreetMap/Nominatim")
        self.assertIsInstance(result["distance_m"], int)

    def test_normalize_reverse_geocode_result_requires_some_address_label(self):
        with self.assertRaisesRegex(LookupError, "adresu"):
            normalize_reverse_geocode_result({}, query_lat=51.0, query_lon=17.0)

    def test_parse_prg_address_features_picks_nearest_address_point(self):
        xml = """
        <wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
            xmlns:ms="http://mapserver.gis.umn.edu/mapserver" xmlns:gml="http://www.opengis.net/gml/3.2">
            <wfs:member>
                <ms:prg-adresy>
                    <ms:msGeometry><gml:Point><gml:pos>359751.072600 363115.146500</gml:pos></gml:Point></ms:msGeometry>
                    <ms:miejscowosc>Wrocław</ms:miejscowosc>
                    <ms:ulica>ul. św. Jerzego</ms:ulica>
                    <ms:numer>5</ms:numer>
                    <ms:kod>50-518</ms:kod>
                </ms:prg-adresy>
            </wfs:member>
            <wfs:member>
                <ms:prg-adresy>
                    <ms:msGeometry><gml:Point><gml:pos>359741.660000 363085.343200</gml:pos></gml:Point></ms:msGeometry>
                    <ms:miejscowosc>Wrocław</ms:miejscowosc>
                    <ms:ulica>ul. św. Jerzego</ms:ulica>
                    <ms:numer>11</ms:numer>
                    <ms:kod>50-518</ms:kod>
                </ms:prg-adresy>
            </wfs:member>
        </wfs:FeatureCollection>
        """

        result = parse_prg_address_features(xml, query_lat=51.08793078, query_lon=17.04468526)

        self.assertEqual(result["formatted"], "ul. św. Jerzego 11, 50-518, Wrocław")
        self.assertEqual(result["road"], "ul. św. Jerzego")
        self.assertEqual(result["house_number"], "11")
        self.assertEqual(result["source"], "prg")
        self.assertEqual(result["source_label"], "PRG/GUGiK")
        self.assertLess(result["distance_m"], 40)

    def test_prg_address_wfs_params_use_puwg1992_bbox(self):
        params = prg_address_wfs_params(51.08793078, 17.04468526, radius_m=160, count=50)

        self.assertEqual(params["TYPENAMES"], "ms:prg-adresy")
        self.assertEqual(params["SRSNAME"], "EPSG:2180")
        self.assertEqual(params["COUNT"], "50")
        self.assertIn("EPSG:2180", params["BBOX"])
        self.assertIn("359", params["BBOX"])
        self.assertIn("363", params["BBOX"])

    def test_lookup_nearest_address_uses_prg_first_and_caches_rounded_coordinates(self):
        class FakeResponse:
            text = """
            <wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
                xmlns:ms="http://mapserver.gis.umn.edu/mapserver" xmlns:gml="http://www.opengis.net/gml/3.2">
                <wfs:member>
                    <ms:prg-adresy>
                        <ms:msGeometry><gml:Point><gml:pos>359741.660000 363085.343200</gml:pos></gml:Point></ms:msGeometry>
                        <ms:miejscowosc>Wrocław</ms:miejscowosc>
                        <ms:ulica>ul. św. Jerzego</ms:ulica>
                        <ms:numer>11</ms:numer>
                        <ms:kod>50-518</ms:kod>
                    </ms:prg-adresy>
                </wfs:member>
            </wfs:FeatureCollection>
            """
            encoding = "utf-8"

            def raise_for_status(self):
                return None

        class FakeSession:
            calls = 0

            def get(self, *args, **kwargs):
                self.calls += 1
                return FakeResponse()

        session = FakeSession()
        public_data._lookup_prg_address_cached.cache_clear()
        public_data._lookup_nominatim_address_cached.cache_clear()
        try:
            with patch.object(public_data.map_downloads, "get_http_session", return_value=session):
                first = public_data.lookup_nearest_address(51.0879301, 17.0446851)
                second = public_data.lookup_nearest_address(51.0879302, 17.0446852)

            self.assertEqual(first["formatted"], "ul. św. Jerzego 11, 50-518, Wrocław")
            self.assertEqual(second["formatted"], first["formatted"])
            self.assertEqual(first["source"], "prg")
            self.assertEqual(session.calls, 1)
        finally:
            public_data._lookup_prg_address_cached.cache_clear()
            public_data._lookup_nominatim_address_cached.cache_clear()

    def test_lookup_nearest_address_falls_back_to_nominatim_when_prg_has_no_match(self):
        class FakeResponse:
            text = "<wfs:FeatureCollection />"
            encoding = "utf-8"

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
        public_data._lookup_prg_address_cached.cache_clear()
        public_data._lookup_nominatim_address_cached.cache_clear()
        try:
            with patch.object(public_data.map_downloads, "get_http_session", return_value=session):
                result = public_data.lookup_nearest_address(51.0879301, 17.0446851)

            self.assertEqual(result["formatted"], "Komuny Paryskiej 73, Wrocław")
            self.assertEqual(result["source"], "nominatim")
            self.assertEqual(session.calls, 2)
        finally:
            public_data._lookup_prg_address_cached.cache_clear()
            public_data._lookup_nominatim_address_cached.cache_clear()


if __name__ == "__main__":
    unittest.main()

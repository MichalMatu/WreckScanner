import unittest

from core.geo import external_map_links


class GeoLinkTests(unittest.TestCase):
    def test_external_map_links_skip_unstable_geoportal_deep_link(self):
        links = external_map_links(51.1, 17.2)

        self.assertIn("street_view", links)
        self.assertIn("google_maps_satellite", links)
        self.assertNotIn("geoportal", links)
        self.assertFalse(any("mapy.geoportal.gov.pl/imap/Imgp_2.html" in value for value in links.values()))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from app.http import rate_limit


class FakeHandler:
    def __init__(self, client_host: str, headers: dict[str, str] | None = None):
        self.client_address = (client_host, 12345)
        self.headers = headers or {}


class HttpRateLimitContractTests(unittest.TestCase):
    def setUp(self):
        rate_limit._BUCKETS.clear()

    def tearDown(self):
        rate_limit._BUCKETS.clear()
        rate_limit._trusted_proxy_networks.cache_clear()

    def test_forwarded_client_header_is_used_only_from_trusted_proxy(self):
        headers = {"X-Forwarded-For": "203.0.113.8"}

        with patch.object(rate_limit.config, "TRUSTED_PROXY_ADDRESSES", ("127.0.0.1",)):
            rate_limit._trusted_proxy_networks.cache_clear()
            self.assertEqual(rate_limit.client_key(FakeHandler("127.0.0.1", headers)), "203.0.113.8")

            rate_limit._trusted_proxy_networks.cache_clear()
            self.assertEqual(rate_limit.client_key(FakeHandler("198.51.100.10", headers)), "198.51.100.10")

    def test_fresh_buckets_are_evicted_when_capacity_is_exceeded(self):
        rate_limit._BUCKETS[("admin-login", "old")].append(1.0)
        rate_limit._BUCKETS[("admin-login", "middle")].append(2.0)
        rate_limit._BUCKETS[("admin-login", "new")].append(3.0)

        with patch.object(rate_limit, "_MAX_RATE_LIMIT_BUCKETS", 2):
            rate_limit._evict_excess_buckets()

        self.assertEqual(len(rate_limit._BUCKETS), 2)
        self.assertNotIn(("admin-login", "old"), rate_limit._BUCKETS)


if __name__ == "__main__":
    unittest.main()

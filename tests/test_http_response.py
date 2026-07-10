import unittest

from core.http_response import read_limited_response_bytes


class LimitedHttpResponseTests(unittest.TestCase):
    def test_rejects_declared_and_streamed_oversized_responses(self):
        class DeclaredOversized:
            headers = {"Content-Length": "11"}

            def iter_content(self, chunk_size=65536):
                raise AssertionError("body must not be read")

        with self.assertRaisesRegex(ValueError, "rozmiar"):
            read_limited_response_bytes(DeclaredOversized(), max_bytes=10)

        class StreamedOversized:
            headers = {}

            def iter_content(self, chunk_size=65536):
                yield b"123456"
                yield b"78901"

        with self.assertRaisesRegex(ValueError, "rozmiar"):
            read_limited_response_bytes(StreamedOversized(), max_bytes=10)

    def test_returns_body_within_limit(self):
        class Response:
            headers = {"Content-Length": "5"}

            def iter_content(self, chunk_size=65536):
                yield b"12"
                yield b"345"

        self.assertEqual(read_limited_response_bytes(Response(), max_bytes=5), b"12345")


if __name__ == "__main__":
    unittest.main()

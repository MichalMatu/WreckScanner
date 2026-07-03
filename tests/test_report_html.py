import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core import report_html


class ReportHtmlTests(unittest.TestCase):
    def test_build_admin_report_html_uses_formal_pdf_like_document(self):
        with TemporaryDirectory() as tmp:
            record_dir = Path(tmp)
            (record_dir / "index.html").write_text(
                """<!doctype html>
<html lang="pl">
<head><meta charset="utf-8"></head>
<body>
<main>
<nav class="link-strip"><a href="https://example.test/street">Street View</a><a href="https://example.test/geo">Geoportal</a></nav>
<section class="evidence photo-upload" data-report-photo-upload>upload controls</section>
<script data-report-photo-upload-script>window.upload = true;</script>
</main>
</body>
</html>
""",
                encoding="utf-8",
            )

            body = report_html.build_admin_report_html(
                record_dir,
                {
                    "id": "wreck_51100000_17200000",
                    "lat": 51.1,
                    "lon": 17.2,
                    "attached_photos": [
                        {
                            "original_filename": "teren.jpg",
                            "public_review_status": "approved",
                            "public_image_file": "photos/approved/public.jpg",
                            "public_thumb_file": "photos/approved/public_thumb.jpg",
                        }
                    ],
                },
                {"created_at": "2026-07-02T14:30:31Z", "crops": [{"label": "2025", "file": "2025.jpg"}]},
                "interwencje@example.test",
                "Temat <test>",
                "Treść <zgłoszenia>",
            ).decode("utf-8")

        self.assertIn("data-report-package-style", body)
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', body)
        self.assertIn("width: min(1080px, calc(100vw - 72px));", body)
        self.assertIn("width: 100%;", body)
        self.assertIn("text-wrap: pretty;", body)
        self.assertIn("Zgłoszenie dotyczące pojazdu nieużytkowanego", body)
        self.assertIn("Data zgłoszenia: 02.07.2026, godz.", body)
        self.assertIn("interwencje@example.test", body)
        self.assertIn("<strong>Dotyczy:</strong> Temat &lt;test&gt;", body)
        self.assertIn("Treść &lt;zgłoszenia&gt;", body)
        self.assertIn("Zdjęcia z miejsca", body)
        self.assertIn("Miniatury historyczne", body)
        self.assertIn('href="photos/approved/public.jpg"', body)
        self.assertIn('src="photos/approved/public_thumb.jpg"', body)
        self.assertIn("miniatury_historyczne/2025.jpg", body)
        self.assertIn("report-photo-figure", body)
        self.assertIn("cursor: pointer", body)
        self.assertIn("data-report-gallery-script", body)
        self.assertIn("data-report-gallery-close", body)
        self.assertLess(body.index("Treść &lt;zgłoszenia&gt;"), body.index("Zdjęcia z miejsca"))
        self.assertNotIn("upload controls", body)
        self.assertNotIn("Street View", body)
        self.assertNotIn("Geoportal", body)
        self.assertNotIn("https://example.test/street", body)
        self.assertNotIn("https://example.test/geo", body)
        self.assertNotIn("data-report-photo-upload-script", body)
        self.assertNotIn("Teczka pojazdu", body)
        self.assertNotIn("Współrzędne:", body)

    def test_build_public_report_html_includes_only_approved_attached_photos(self):
        body = report_html.build_public_report_html(
            {
                "id": "wreck_51100000_17200000",
                "lat": 51.1,
                "lon": 17.2,
                "attached_photos": [
                    {
                        "public_review_status": "approved",
                        "public_image_file": "photos/approved/public.jpg",
                        "public_thumb_file": "photos/approved/public_thumb.jpg",
                    },
                    {
                        "public_review_status": "pending",
                        "public_image_file": "photos/pending/public.jpg",
                        "public_thumb_file": "photos/pending/public_thumb.jpg",
                    },
                ],
            },
            {"crops": [{"label": "2025", "file": "2025.jpg"}]},
            "Raport",
            "Link do miejsca:\nhttps://wreckscanner.pl/?lat=51.100000&lon=17.200000&z=20&photo=photo_test",
        ).decode("utf-8")

        self.assertIn("miniatury_historyczne/2025.jpg", body)
        self.assertIn('href="photos/approved/public.jpg"', body)
        self.assertIn('src="photos/approved/public_thumb.jpg"', body)
        self.assertNotIn("zdjecia_z_miejsca", body)
        self.assertNotIn("photos/pending/public.jpg", body)
        self.assertNotIn("photos/pending/public_thumb.jpg", body)
        self.assertIn("Otwórz miejsce w WreckScanner", body)
        self.assertIn('class="report-inline-link"', body)
        self.assertIn(
            'href="https://wreckscanner.pl/?lat=51.100000&amp;lon=17.200000&amp;z=20&amp;photo=photo_test"',
            body,
        )
        self.assertLess(body.index("Otwórz miejsce w WreckScanner"), body.index("Miniatury historyczne"))


if __name__ == "__main__":
    unittest.main()

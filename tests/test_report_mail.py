import unittest

from core.report_mail import build_mail_draft


class ReportMailTests(unittest.TestCase):
    def test_build_mail_draft_includes_reporter_history_and_evidence_labels_without_map_links(self):
        subject, body = build_mail_draft(
            {
                "id": "wreck_51100000_17200000",
                "lat": 51.1,
                "lon": 17.2,
                "links": {"street_view": "https://example.test/street"},
                "report_history": [
                    {
                        "created_at": "2026-06-01T10:00:00Z",
                        "package_id": "report_20260601T100000Z_deadbeef",
                        "public": True,
                    }
                ],
            },
            {"labels_present": ["2024", "2025"]},
            {
                "reporter_name": "Jan Kowalski",
                "reporter_address": "ul. Testowa 1, Wrocław",
                "reporter_phone": "500 600 700",
                "reporter_email": "jan@example.com",
                "location_description": "ul. Długa 10, parking przy szkole",
                "observed_at": "2026-06-02T12:30",
                "vehicle_description": "Pojazd zabrudzony, długo stoi w tym samym miejscu.",
            },
        )

        self.assertEqual(subject, "Zgłoszenie pojazdu nieużytkowanego - ul. Długa 10, parking przy szkole")
        self.assertIn("- Imię i nazwisko: Jan Kowalski", body)
        self.assertIn("- pojazd widoczny na ortofotomapach z lat: 2024, 2025", body)
        self.assertIn("report_20260601T100000Z_deadbeef (publiczny)", body)
        self.assertNotIn("Linki do weryfikacji", body)
        self.assertNotIn("Street View", body)
        self.assertNotIn("https://example.test/street", body)


if __name__ == "__main__":
    unittest.main()

import unittest

from core.report_mail import build_mail_draft


class ReportMailTests(unittest.TestCase):
    def test_build_mail_draft_includes_reporter_and_evidence_labels_without_technical_noise(self):
        subject, body = build_mail_draft(
            {
                "id": "wreck_51100000_17200000",
                "lat": 51.1,
                "lon": 17.2,
                "links": {"street_view": "https://example.test/street"},
                "vehicle_insurance_status": "uninsured",
                "vehicle_insurance_checked_at": "2026-07-05T12:30:00Z",
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
        self.assertIn("02.06.2026, godz. 12:30", body)
        self.assertNotIn("2026-06-02T12:30", body)
        self.assertIn("- pojazd widoczny na ortofotomapach z lat: 2024, 2025", body)
        self.assertIn("Status OC/UFG pojazdu", body)
        self.assertIn("- Wynik ręcznego sprawdzenia: brak OC", body)
        self.assertIn("- Data sprawdzenia w UFG: 05.07.2026, godz. 12:30", body)
        self.assertIn("Zakres oczekiwanej odpowiedzi", body)
        self.assertIn("art. 241 Kodeksu postępowania administracyjnego", body)
        self.assertIn("art. 237 § 1 oraz art. 244 § 1 i § 2", body)
        self.assertIn("Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne", body)
        self.assertNotIn("pakiet dowodowy ZIP", body)
        self.assertNotIn("W załączniku", body)
        self.assertNotIn("Historia działań", body)
        self.assertNotIn("report_20260601T100000Z_deadbeef", body)
        self.assertNotIn("lokalna sprawa", body)
        self.assertNotIn("wreck_51100000_17200000", body)
        self.assertNotIn("Linki do weryfikacji", body)
        self.assertNotIn("Street View", body)
        self.assertNotIn("https://example.test/street", body)

    def test_build_mail_draft_shortens_subject_at_word_boundary(self):
        subject, _body = build_mail_draft(
            {
                "id": "wreck_51100000_17200000",
                "lat": 51.1,
                "lon": 17.2,
                "links": {},
            },
            {"labels_present": []},
            {
                "reporter_name": "Jan Kowalski",
                "reporter_address": "ul. Testowa 1, Wrocław",
                "reporter_phone": "500 600 700",
                "reporter_email": "jan@example.com",
                "location_description": (
                    "Pojazd stoi przy wewnętrznym ciągu komunikacyjnym obok parkingu "
                    "osiedlowego, w bezpośrednim sąsiedztwie przejścia dla pieszych"
                ),
                "observed_at": "2026-06-02T12:30",
                "vehicle_description": "Pojazd długo stoi w tym samym miejscu.",
            },
        )

        location_part = subject.removeprefix("Zgłoszenie pojazdu nieużytkowanego - ")
        self.assertLessEqual(len(location_part), 90)
        self.assertTrue(location_part.endswith("..."))
        self.assertIn("parkingu osiedlowego...", location_part)
        self.assertNotIn(" w...", location_part)
        self.assertNotIn("bezpośredni...", location_part)

    def test_build_mail_draft_omits_insurance_check_date_when_status_is_unknown(self):
        _subject, body = build_mail_draft(
            {
                "id": "wreck_51100000_17200000",
                "lat": 51.1,
                "lon": 17.2,
                "links": {},
                "vehicle_insurance_status": "unknown",
                "vehicle_insurance_checked_at": None,
            },
            {"labels_present": []},
            {
                "reporter_name": "Jan Kowalski",
                "reporter_address": "ul. Testowa 1, Wrocław",
                "reporter_phone": "500 600 700",
                "reporter_email": "jan@example.com",
                "location_description": "ul. Długa 10, parking przy szkole",
                "observed_at": "2026-06-02T12:30",
                "vehicle_description": "Pojazd długo stoi w tym samym miejscu.",
            },
        )

        self.assertIn("- Wynik ręcznego sprawdzenia: nie sprawdzono", body)
        self.assertNotIn("Data sprawdzenia w UFG", body)


if __name__ == "__main__":
    unittest.main()

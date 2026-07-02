from __future__ import annotations

from datetime import datetime
from typing import Any


def _first_line(value: str, max_len: int = 90) -> str:
    text = " ".join(value.split())
    return text[:max_len].rstrip() or "lokalizacja"


def _labels_text(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    labels = record.get("labels_present") or evidence.get("labels_present") or []
    return ", ".join(str(label) for label in labels) or "brak danych"


def _field_datetime_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "brak danych"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    return parsed.strftime("%d.%m.%Y, godz. %H:%M")


def _formal_requests_text() -> str:
    return """Wnoszę o potraktowanie niniejszego pisma jako wniosku w rozumieniu art. 241 Kodeksu postępowania administracyjnego, a jeżeli organ uzna to za właściwe - jako skargi/wniosku w trybie działu VIII Kodeksu postępowania administracyjnego.

Wnoszę także o zawiadomienie mnie o sposobie załatwienia sprawy w terminie wynikającym z art. 237 § 1 oraz art. 244 § 1 i § 2 Kodeksu postępowania administracyjnego.

Wnoszę o:
- formalną weryfikację, czy pojazd spełnia przesłanki pojazdu nieużytkowanego lub zalegającego w przestrzeni publicznej,
- wskazanie komórki, jednostki albo osoby odpowiedzialnej za dalsze czynności,
- informację, czy sprawa była już wcześniej zgłaszana lub procedowana,
- informację, jakie czynności podjęto dotychczas i z jakim wynikiem,
- nadanie albo wskazanie numeru sprawy,
- odpowiedź, czy planowane jest usunięcie pojazdu, wezwanie właściciela, kontrola patrolu albo przekazanie sprawy innemu organowi,
- pisemną odpowiedź obejmującą każdy z powyższych punktów."""


def build_mail_draft(record: dict[str, Any], evidence: dict[str, Any], fields: dict[str, str]) -> tuple[str, str]:
    lat = float(record.get("lat"))
    lon = float(record.get("lon"))
    labels = _labels_text(record, evidence)
    subject = f"Zgłoszenie pojazdu nieużytkowanego - {_first_line(fields['location_description'])}"
    body = f"""Dzień dobry,

zgłaszam pojazd, który wygląda na długotrwale nieużytkowany.

Dane osoby zgłaszającej:
- Imię i nazwisko: {fields["reporter_name"]}
- Adres zamieszkania: {fields["reporter_address"]}
- Telefon: {fields["reporter_phone"]}
- E-mail: {fields["reporter_email"]}

Miejsce pojazdu:
{fields["location_description"]}

Współrzędne GPS:
{lat:.6f}, {lon:.6f}

Data i godzina obserwacji:
{_field_datetime_text(fields["observed_at"])}

Opis stanu pojazdu:
{fields["vehicle_description"]}

Materiał pomocniczy z aplikacji WreckScanner:
- pojazd widoczny na ortofotomapach z lat: {labels}

Zakres oczekiwanej odpowiedzi:
{_formal_requests_text()}

Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne dołączone do niniejszego zgłoszenia. Proszę o weryfikację przez patrol i podjęcie czynności w sprawie pojazdu nieużytkowanego.

Z poważaniem,
{fields["reporter_name"]}
"""
    return subject, body

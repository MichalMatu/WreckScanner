from __future__ import annotations

from datetime import datetime
from typing import Any

from core import config
from core.cadastral import cadastral_code_label
from core.field_photo_metadata import vehicle_insurance_status_label

DANGLING_SUBJECT_WORDS = {"i", "o", "u", "w", "z", "do", "na", "od", "po"}


def _first_line(value: str, max_len: int = 90) -> str:
    text = " ".join(value.split())
    if not text:
        return "lokalizacja"
    if len(text) <= max_len:
        return text
    suffix = "..."
    limit = max(max_len - len(suffix), 1)
    trimmed = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:-")
    if not trimmed:
        trimmed = text[:limit].rstrip(" ,.;:-")
    words = trimmed.rsplit(" ", 1)
    if len(words) == 2 and words[1].lower().strip(" ,.;:-") in DANGLING_SUBJECT_WORDS:
        trimmed = words[0].rstrip(" ,.;:-")
    return f"{trimmed}{suffix}" if trimmed else "lokalizacja"


def _labels_text(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    labels = record.get("labels_present") or evidence.get("labels_present") or []
    return ", ".join(str(label) for label in labels) or "brak danych"


def _place_url_text(record: dict[str, Any]) -> str:
    return str(record.get("place_url") or "").strip()


def _parcel_line(label: str, value: Any, suffix: str = "") -> str:
    text = str(value or "").strip()
    return f"- {label}: {text}{suffix}" if text else ""


def _parcel_context_text(record: dict[str, Any]) -> str:
    parcel = record.get("parcel") if isinstance(record.get("parcel"), dict) else {}
    if parcel:
        terrain_type = cadastral_code_label(parcel.get("land_use") or parcel.get("contour"))
        lines = [
            "Dane działki ewidencyjnej (pomocniczo, bez danych właściciela):",
            _parcel_line("Numer działki", parcel.get("parcel_number")),
            _parcel_line("Typ terenu", terrain_type),
            _parcel_line("Identyfikator działki", parcel.get("parcel_id")),
            _parcel_line("Obręb", parcel.get("district")),
            _parcel_line("Gmina", parcel.get("municipality")),
            _parcel_line("Powiat", parcel.get("county")),
            _parcel_line("Województwo", parcel.get("voivodeship")),
            _parcel_line("Grupa rejestrowa", parcel.get("registry_group")),
            _parcel_line("Data publikacji danych", parcel.get("published_at")),
        ]
        return "\n".join(line for line in lines if line)
    parcel_error = str(record.get("parcel_error") or "").strip()
    if parcel_error:
        return f"Dane działki ewidencyjnej (pomocniczo):\n- {parcel_error}"
    return ""


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


def _vehicle_insurance_context_text(record: dict[str, Any]) -> str:
    status = str(record.get("vehicle_insurance_status") or config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS)
    lines = [
        "Status OC/UFG pojazdu:",
        f"- Wynik ręcznego sprawdzenia: {vehicle_insurance_status_label(status)}",
    ]
    if status != config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS:
        lines.append(f"- Data sprawdzenia w UFG: {_field_datetime_text(record.get('vehicle_insurance_checked_at'))}")
    return "\n".join(lines)


def build_mail_draft(record: dict[str, Any], evidence: dict[str, Any], fields: dict[str, str]) -> tuple[str, str]:
    lat = float(record.get("lat"))
    lon = float(record.get("lon"))
    labels = _labels_text(record, evidence)
    place_url = _place_url_text(record)
    place_section = f"\nLink do miejsca w IleStoi.pl:\n{place_url}\n" if place_url else ""
    parcel_context = _parcel_context_text(record)
    parcel_section = f"\n{parcel_context}\n" if parcel_context else ""
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
{place_section}{parcel_section}

Data i godzina obserwacji:
{_field_datetime_text(fields["observed_at"])}

Opis stanu pojazdu:
{fields["vehicle_description"]}

{_vehicle_insurance_context_text(record)}

Materiał pomocniczy z aplikacji IleStoi.pl:
- pojazd widoczny na ortofotomapach z lat: {labels}

Zakres oczekiwanej odpowiedzi:
{_formal_requests_text()}

Materiał dowodowy stanowią zdjęcia z miejsca oraz miniatury historyczne dołączone do niniejszego zgłoszenia. Proszę o weryfikację przez patrol i podjęcie czynności w sprawie pojazdu nieużytkowanego.

Z poważaniem,
{fields["reporter_name"]}
"""
    return subject, body

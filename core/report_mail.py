from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from core import config
from core.cadastral import cadastral_code_label
from core.field_photo_metadata import vehicle_insurance_status_label

DANGLING_SUBJECT_WORDS = {"i", "o", "u", "w", "z", "do", "na", "od", "po"}
REPORT_TIMEZONE = ZoneInfo("Europe/Warsaw")


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


def _terrain_type(parcel: dict[str, Any]) -> str:
    return cadastral_code_label(parcel.get("land_use") or parcel.get("contour"))


def _parcel_reference(parcel: dict[str, Any]) -> str:
    number = str(parcel.get("parcel_number") or "").strip()
    parcel_id = str(parcel.get("parcel_id") or "").strip()
    if number and parcel_id:
        return f"działka {number}, identyfikator {parcel_id}"
    if number:
        return f"działka {number}"
    if parcel_id:
        return f"działka o identyfikatorze {parcel_id}"
    return "wskazana działka"


def _parcel_context_text(record: dict[str, Any]) -> str:
    parcel = record.get("parcel") if isinstance(record.get("parcel"), dict) else {}
    if parcel:
        terrain_type = _terrain_type(parcel)
        terrain_clause = f"ma użytek \"{terrain_type}\"" if terrain_type else "ma nieustalony automatycznie typ użytku"
        return (
            "Dane działki ewidencyjnej (pomocniczo): według danych ewidencyjnych "
            f"{_parcel_reference(parcel)} {terrain_clause}; proszę jednak o Państwa własną ocenę, "
            "czy miejsce znajduje się na drodze publicznej, w strefie zamieszkania albo w strefie ruchu."
        )
    parcel_error = str(record.get("parcel_error") or "").strip()
    if parcel_error:
        return (
            "Dane działki ewidencyjnej (pomocniczo): nie udało się automatycznie pobrać danych "
            f"działki ({parcel_error}); proszę o Państwa własną ocenę statusu miejsca."
        )
    return ""


def _field_datetime_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "brak danych"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(REPORT_TIMEZONE)
    return parsed.strftime("%d.%m.%Y, godz. %H:%M")


def _vehicle_insurance_context_text(record: dict[str, Any]) -> str:
    status = str(record.get("vehicle_insurance_status") or config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS)
    if status == config.DEFAULT_FIELD_PHOTO_VEHICLE_INSURANCE_STATUS:
        return ""
    lines = [
        "Informacja pomocnicza o OC:",
        f"- Ręczne sprawdzenie w UFG: {vehicle_insurance_status_label(status)}",
    ]
    lines.append(f"- Data sprawdzenia w UFG: {_field_datetime_text(record.get('vehicle_insurance_checked_at'))}")
    lines.append("- Proszę potraktować tę informację pomocniczo i zweryfikować ją we własnym zakresie.")
    return "\n".join(lines)


def _optional_section(value: str) -> str:
    text = str(value or "").strip()
    return f"\n{text}\n" if text else ""


def build_mail_draft(record: dict[str, Any], evidence: dict[str, Any], fields: dict[str, str]) -> tuple[str, str]:
    lat = float(record.get("lat"))
    lon = float(record.get("lon"))
    labels = _labels_text(record, evidence)
    parcel_context = _parcel_context_text(record)
    parcel_section = _optional_section(parcel_context)
    insurance_section = _optional_section(_vehicle_insurance_context_text(record))
    subject = f"Zgłoszenie pojazdu nieużytkowanego - {_first_line(fields['location_description'])}"
    body = f"""Dzień dobry,

zgłaszam pojazd, który według mojej obserwacji może spełniać przesłanki z art. 50a ust. 1 Prawa o ruchu drogowym.

Dane zgłaszającego:
- Imię i nazwisko: {fields["reporter_name"]}
- Miejsce zamieszkania: {fields["reporter_address"]}
- E-mail: {fields["reporter_email"]}
- Telefon: {fields["reporter_phone"]}

Miejsce pojazdu:
{fields["location_description"]}

Współrzędne GPS:
{lat:.6f}, {lon:.6f}

Data i godzina obserwacji:
{_field_datetime_text(fields["observed_at"])}

Opis stanu pojazdu:
{fields["vehicle_description"]}
{insurance_section}{parcel_section}
Załączniki:
- zdjęcia z miejsca,
- materiał pomocniczy z miniaturami historycznymi ortofoto z lat: {labels}.

Miniatury historyczne mogą wskazywać na długotrwałą obecność pojazdu w tym rejonie, ale nie zastępują oględzin w terenie.

Proszę o weryfikację przez patrol i podjęcie czynności przewidzianych prawem. Jeżeli miejsce nie należy do właściwości Straży Miejskiej, uprzejmie proszę o przekazanie zgłoszenia właściwej jednostce albo o wskazanie właściwego zarządcy/podmiotu.

Z poważaniem,
{fields["reporter_name"]}
"""
    return subject, body

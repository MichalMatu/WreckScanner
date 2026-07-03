from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REQUIRED_REPORT_FIELDS = {
    "reporter_name": "imię i nazwisko",
    "reporter_address": "adres zamieszkania",
    "reporter_phone": "telefon",
    "reporter_email": "adres e-mail",
    "location_description": "dokładne miejsce pojazdu",
    "observed_at": "data i godzina obserwacji",
    "vehicle_description": "opis stanu pojazdu",
}


def safe_text(value: Any, max_len: int = 4000) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) > max_len:
        raise ValueError("Jedno z pól formularza jest zbyt długie.")
    return text


def validate_report_fields(raw_fields: dict[str, str]) -> dict[str, str]:
    fields = {key: safe_text(raw_fields.get(key)) for key in REQUIRED_REPORT_FIELDS}
    missing = [label for key, label in REQUIRED_REPORT_FIELDS.items() if not fields[key]]
    if missing:
        raise ValueError("Uzupełnij wymagane pola: " + ", ".join(missing) + ".")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", fields["reporter_email"]):
        raise ValueError("Podaj prawidłowy adres e-mail zgłaszającego.")
    return fields


def safe_filename(raw_name: str, fallback: str, ext: str) -> str:
    stem = Path(raw_name or "").stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or fallback
    stem = stem[:70]
    return f"{stem}{ext}"

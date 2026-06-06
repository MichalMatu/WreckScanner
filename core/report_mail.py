from __future__ import annotations

from typing import Any


def _first_line(value: str, max_len: int = 90) -> str:
    text = " ".join(value.split())
    return text[:max_len].rstrip() or "lokalizacja"


def _labels_text(record: dict[str, Any], evidence: dict[str, Any]) -> str:
    labels = record.get("labels_present") or evidence.get("labels_present") or []
    return ", ".join(str(label) for label in labels) or "brak danych"


def _links_text(links: dict[str, Any]) -> str:
    labels = {
        "street_view": "Google Street View",
        "google_maps_satellite": "Google Maps satelita",
        "apple_maps": "Apple Maps",
        "mapillary": "Mapillary",
        "geoportal": "Geoportal Krajowy",
    }
    lines = []
    for key, label in labels.items():
        url = links.get(key)
        if url:
            lines.append(f"- {label}: {url}")
    return "\n".join(lines) or "- brak linków"


def _report_history_text(record: dict[str, Any]) -> str:
    history = record.get("report_history") if isinstance(record.get("report_history"), list) else []
    if not history:
        return "- brak wcześniejszych pakietów zgłoszeniowych zapisanych w tej sprawie"
    lines = []
    for item in history[-5:]:
        if not isinstance(item, dict):
            continue
        created_at = str(item.get("created_at") or "brak daty")
        package_id = str(item.get("package_id") or "brak id")
        mode = "publiczny" if item.get("public") else "administracyjny"
        lines.append(f"- {created_at}: pakiet {package_id} ({mode})")
    return "\n".join(lines) or "- brak wcześniejszych pakietów zgłoszeniowych zapisanych w tej sprawie"


def _formal_requests_text(record: dict[str, Any]) -> str:
    return f"""Wnoszę o:
- formalną weryfikację, czy pojazd spełnia przesłanki pojazdu nieużytkowanego lub zalegającego w przestrzeni publicznej,
- wskazanie komórki, jednostki albo osoby odpowiedzialnej za dalsze czynności,
- informację, czy sprawa była już wcześniej zgłaszana lub procedowana,
- informację, jakie czynności podjęto dotychczas i z jakim wynikiem,
- nadanie albo wskazanie numeru sprawy,
- odpowiedź, czy planowane jest usunięcie pojazdu, wezwanie właściciela, kontrola patrolu albo przekazanie sprawy innemu organowi,
- pisemną odpowiedź obejmującą każdy z powyższych punktów.

Historia działań zapisana w WreckScanner:
{_report_history_text(record)}"""


def build_mail_draft(record: dict[str, Any], evidence: dict[str, Any], fields: dict[str, str]) -> tuple[str, str]:
    lat = float(record.get("lat"))
    lon = float(record.get("lon"))
    labels = _labels_text(record, evidence)
    score = float(record.get("best_score") or evidence.get("score") or 0.0)
    links = record.get("links") or evidence.get("links") or {}
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
{fields["observed_at"]}

Opis stanu pojazdu:
{fields["vehicle_description"]}

Materiał pomocniczy z aplikacji WreckScanner:
- lokalna sprawa: {record.get("id")}
- pojazd widoczny na ortofotomapach z lat: {labels}
- najlepszy score analizy: {score * 100:.0f}%

Linki do weryfikacji miejsca:
{_links_text(links)}

Zakres oczekiwanej odpowiedzi:
{_formal_requests_text(record)}

W załączniku dołączam pakiet dowodowy ZIP z miniaturami historycznymi, zdjęciami z miejsca oraz metadanymi analizy. Proszę o weryfikację przez patrol i podjęcie czynności w sprawie pojazdu nieużytkowanego.

Z poważaniem,
{fields["reporter_name"]}
"""
    return subject, body

# Current Data And UX Model

Ten dokument opisuje aktualny wzorzec dzialania WreckScanner po usunieciu starego
modelu trwalych spraw pojazdow.

## Zrodlo prawdy

- `zdjecia_terenowe/` - jedyne rekordy obserwacji pokazywane na mapie.
- `prywatne_zdjecia/field_photos/` - prywatne oryginaly zdjec terenowych.
- `zgloszenia_prywatnosci/` - kolejka zgloszen prywatnosci.
- `settings.json` - lokalne ustawienia aplikacji.

Kazde zdjecie terenowe musi miec jawne `issue_type`. Warstwa pojazdow jest
budowana z zatwierdzonych zdjec terenowych o `issue_type: "vehicle"`.

## Aktualne przeplywy

- Dodanie materialu tworzy rekord zdjecia terenowego z tokenem edycji.
- Administrator zatwierdza albo odrzuca zdjecia w jednej kolejce photo review.
- Pojazdy na mapie sa grupami zatwierdzonych zdjec terenowych, nie osobnymi
  rekordami spraw.
- Zgloszenie ZIP/PDF jest generowane na zadanie z listy `field_photo.id` i
  wspolrzednych grupy.
- Miniatury ortofoto sa dowodem generowanym podczas tworzenia pakietu raportu.

## Endpointy domenowe

- `GET /api/field-photos`
- `POST /api/field-photos`
- `PATCH /api/field-photos/:id/location`
- `POST /api/field-photo-reports/report-package`
- `GET /api/admin/photos`
- `PATCH /api/admin/photos/field/:id/review`
- `DELETE /api/admin/photos/field/:id`

Nie ma publicznego ani administracyjnego API `/api/wrecks`.

## Zakazane artefakty

Te nazwy nie powinny wystepowac w kodzie runtime ani dokumentacji aktualnego
modelu:

- `/api/wrecks`
- `WRECKS_DIR`, `WRECKS_URL`, `WRECKS_ROUTE`
- `zidentyfikowane_wraki`
- `wreck_photos`
- `attached_wreck`
- `saved_wrecks`
- `wreck_review`
- `manual_wrecks`
- `vehicle case` jako encja aplikacji

Wyjatkiem sa testy antyregresyjne, ktore sprawdzaja, ze te nazwy nie wracaja,
oraz dokument przyszlej bazy, ktory wymienia wycofane tabele jako niedozwolone.

## Audyt domkniecia

```bash
rg -n -i '(/api/wrecks|zidentyfikowane_wraki|wreck_photos|attached_wreck|saved_wreck|saved-wreck|manual_wreck|WRECKS_DIR|WRECKS_URL|WRECKS_ROUTE|saved_wrecks|wreck_review)' app core scripts web README.md pyproject.toml

test ! -e zidentyfikowane_wraki
test ! -e prywatne_zdjecia/wreck_photos

find zdjecia_terenowe -name record.json -print0 \
  | xargs -0 jq -r 'select(has("issue_type")|not) | input_filename'

find zdjecia_terenowe -name record.json -print0 \
  | xargs -0 rg -l '"(original_file|thumbnail_file|thumb_file|original_url|original_path)"'

./scripts/check.sh
```

Oczekiwany wynik: dwa polecenia `find` nic nie wypisuja, katalogi starego modelu
nie istnieja, a `scripts/check.sh` konczy sie statusem OK.

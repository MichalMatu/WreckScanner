# Current Data And UX Model

Ten dokument opisuje aktualny wzorzec dzialania IleStoi.pl po usunieciu starego
modelu trwalych spraw pojazdow.

## Zrodlo prawdy

- `wreckscanner.sqlite3` - aktywny stan aplikacji: `field_photos`,
  `settings`, `privacy_requests`.
- `zdjecia_terenowe/` - publiczne pliki zdjec terenowych i katalogi robocze
  pochodnych obrazow.
- `prywatne_zdjecia/field_photos/` - prywatne oryginaly zdjec terenowych.
- `settings.json` i `zgloszenia_prywatnosci/` - format importu/migracji i
  backup historyczny, nie aktywny runtime.

Kazde zdjecie terenowe musi miec jawne `issue_type`. Warstwa pojazdow jest
budowana z zatwierdzonych zdjec terenowych o `issue_type: "vehicle"`.
Status OC/UFG jest recznie zapisywany jako `vehicle_insurance_status`:
`unknown`, `insured` albo `uninsured`. Dla recznie sprawdzonych statusow
`insured` i `uninsured` aplikacja zapisuje tez `vehicle_insurance_checked_at`,
czyli date zapisania wyniku sprawdzenia w UFG. Aplikacja nie pobiera danych z UFG automatycznie
i nie zapisuje tablic ani VIN.

## Aktualne przeplywy

- Dodanie materialu tworzy rekord `field_photos` w SQLite z tokenem edycji.
- Administrator zatwierdza albo odrzuca zdjecia w jednej kolejce photo review.
- Pojazdy na mapie sa grupami zatwierdzonych zdjec terenowych, nie osobnymi
  rekordami spraw.
- Zmiana OC/UFG w panelu admina aktualizuje wszystkie zdjecia pojazdu w tej
  samej grupie mapy. Edycja wlasciciela przez token dotyczy tylko jego zdjecia
  i wraca do kolejki review.
- Zgloszenie ZIP/PDF jest generowane na zadanie z listy `field_photo.id` i
  wspolrzednych grupy.
- Zgloszenie zawiera tekstowy wynik recznego sprawdzenia OC/UFG oraz date
  sprawdzenia w mailu, `zgloszenie.txt`, `raport.html` i PDF.
- Miniatury ortofoto sa dowodem generowanym podczas tworzenia pakietu raportu.
- Raporty, cropy mapy i paczki ZIP/PDF nie sa zapisywane w DB ani w stalym
  katalogu runtime.

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
test ! -e prywatne_zgloszenia

./.venv/bin/python scripts/migrate_json_to_db.py --validate-only

./scripts/check.sh
```

Oczekiwany wynik: walidacja DB pokazuje zgodne liczniki i `Brakujace sciezki: 0`,
katalogi starego modelu nie istnieja, diagnostyka danych nie widzi starych
pakietow raportow, a `scripts/check.sh` konczy sie statusem OK.

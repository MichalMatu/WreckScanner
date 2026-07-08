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

Status skutecznosci zgłoszenia pojazdu jest zapisany bez osobnej encji sprawy
jako `vehicle_resolution_status`: `active` albo `removed`. Domyslnie kazde
zdjecie pojazdu jest `active`; przy zmianie statusu aplikacja zapisuje
`vehicle_resolution_updated_at`. Usuniety pojazd moze pozostac na mapie jako
zanonimizowany wpis sukcesu ukryty domyslnie filtrem warstwy pojazdow.

## Aktualne przeplywy

- Dodanie materialu tworzy rekord `field_photos` w SQLite z tokenem edycji.
- Publiczny upload uzytkownika najpierw tworzy szkic `draft`; wlasciciel moze
  go zanonimizowac, wyslac do weryfikacji albo usunac tokenem.
- Po wyslaniu do weryfikacji rekord przechodzi do `pending`. Pozostaje widoczny
  na mapie zgodnie z ustawieniami warstw, a wlasciciel z poprawnym tokenem moze
  nadal edytowac anonimizacje albo usunac swoje oczekujace zgloszenie.
- Administrator zatwierdza albo odrzuca zdjecia w jednej kolejce photo review.
- Pojazdy na mapie sa grupami zatwierdzonych zdjec terenowych, nie osobnymi
  rekordami spraw.
- Zmiana OC/UFG w panelu admina aktualizuje wszystkie zdjecia pojazdu w tej
  samej grupie mapy. Edycja wlasciciela przez token dotyczy tylko jego zdjecia
  i wraca do kolejki review.
- Administrator moze oznaczyc grupe pojazdu jako usunieta albo przywrocic ja
  jako aktywna. Grupa jest traktowana jako usunieta tylko wtedy, gdy wszystkie
  zatwierdzone zdjecia pojazdu w tej grupie maja `vehicle_resolution_status:
  "removed"`.
- Publiczna mapa domyslnie ukrywa usuniete pojazdy, ale tray filtrow warstwy
  `Pojazdy` pozwala je pokazac albo wyswietlic tylko usuniete.
- Zgloszenie PDF jest generowane na zadanie z listy `field_photo.id` i
  wspolrzednych grupy.
- Zgloszenie zawiera tekstowy wynik recznego sprawdzenia OC/UFG oraz date
  sprawdzenia w tresci PDF.
- Zgloszenie PDF nie jest generowane dla grupy oznaczonej w calosci jako
  usunieta.
- Miniatury ortofoto sa dowodem generowanym podczas tworzenia raportu PDF.
- Raporty PDF i cropy mapy nie sa zapisywane w DB ani w stalym
  katalogu runtime.

## Endpointy domenowe

- `GET /api/field-photos`
- `POST /api/field-photos`
- `PATCH /api/field-photos/:id/location`
- `POST /api/field-photos/owner-claim`
- `POST /api/field-photos/owner-submit`
- `POST /api/field-photos/owner-discard`
- `POST /api/field-photos/owner-delete`
- `PATCH /api/field-photos/:id/owner-review`
- `POST /api/field-photo-reports/report-pdf`
- `GET /api/admin/photos`
- `PATCH /api/admin/photos/field/:id/review`
- `DELETE /api/admin/photos/field/:id`

`PATCH /api/admin/photos/field/:id/review` moze zapisac sama decyzje
`vehicle_resolution_status` bez zmiany statusu moderacji lub redakcji. Taka
aktualizacja obejmuje cala grupe pojazdu w promieniu grupowania mapy.

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

# Future Database Contract

Ten dokument opisuje docelowy model bazy danych po rozplątaniu starego wzorca spraw.
Nie jest instrukcją uruchomienia bazy teraz. To kontrakt dla przyszłej migracji.

## Decyzja storage

Pierwszy produkcyjny storage to SQLite z trybem WAL:

- jeden lokalny operator aplikacji i lokalny katalog zdjęć nie wymagają PostgreSQL,
- plik bazy łatwo objąć backupem razem z katalogami zdjęć,
- WAL daje bezpieczniejsze współdzielenie krótkich odczytów i zapisów,
- PostgreSQL zostaje opcją dopiero dla równoległego hostingu wielu operatorów.

Migracje SQL są w `database/migrations/`. Runtime nie może tworzyć tabel poza
kontraktem opisanym niżej.

## Źródło prawdy

Docelowa baza ma przejąć tylko dane użytkowe, które są stanem aplikacji:

- `field_photos` - zdjęcia terenowe, ich lokalizacja, typ obserwacji, status przeglądu, redakcje, publiczne pochodne i ścieżka prywatnego oryginału.
- `settings` - trwałe ustawienia aplikacji i publicznych przełączników.
- `privacy_requests` - zgłoszenia prywatności oraz ich status obsługi.

Małe tabele pomocnicze są dopuszczalne tylko wtedy, gdy normalizują powyższe dane bez tworzenia nowej domeny. Przykłady: `schema_migrations`, historia zmian statusu prywatności, tokeny edycji zdjęć, kontrolowane słowniki typów obserwacji.

## Czego nie modelować

Następujące rzeczy nie mogą stać się tabelami ani trwałym API bazy:

- `reports` - raport jest generowany na żądanie do pobrania.
- `report_packages` - pakiety ZIP/PDF nie są stanem aplikacji.
- `public_report_packages` - publiczny raport także pozostaje jednorazowym wynikiem.
- `map_crops` - wycinki map są tymczasowym dowodem tworzonym podczas generowania raportu.
- `report_crops` - crop raportowy nie jest rekordem domenowym.
- `evidence_crops` - historyczny crop dowodowy nie jest tabelą.
- `wrecks` - stare teczki pojazdów nie są docelową domeną aplikacji.
- `vehicle_cases` - sprawa pojazdu nie jest encją przyszłej bazy.
- `cases` - ogólny model spraw nie jest potrzebny w tym produkcie.
- `evidences` - dowody raportowe są składane tymczasowo z danych zdjęć terenowych i map.

## Minimalny szkic tabel

`field_photos`

- `id`
- `created_at`, `captured_at`
- `issue_type`
- `lat`, `lon`, `coordinate_source`, `position_updated_at`
- `public_review_status`, `reviewed_at`, `redactions`
- `original_filename`, `content_type`, `format`, `size_bytes`, `image_width`, `image_height`
- `private_original_file`, `public_image_file`, `public_thumb_file`, `public_width`, `public_height`
- `submission_owner`
- `edit_token_salt`, `edit_token_hash`, `edit_token_created_at`
- `links`

`settings`

- `key`
- `value_json`
- `updated_at`

`privacy_requests`

- `id`
- `created_at`, `updated_at`
- `status`
- `photo_scope`, `photo_id`
- `requester_contact`
- `reason`
- `notes`

## Zasady migracji

1. Importuj zdjęcia z `zdjecia_terenowe/` jako główne rekordy `field_photos`.
2. Importuj ustawienia z `settings.json` do `settings`.
3. Importuj `zgloszenia_prywatnosci/` do `privacy_requests`.
4. Nie importuj `prywatne_zgloszenia/`.
5. Nie importuj `evidence/report_*` ani wygenerowanych cropów map.
6. Nie importuj dawnych katalogów archiwalnych teczek pojazdów; zdjęcia muszą istnieć jako `field_photos`.

Raportowanie ma działać przez listę `field_photo.id` oraz współrzędne grupy zdjęć. Pliki ZIP/PDF i cropy mapy pozostają wynikiem jednorazowym, zwracanym użytkownikowi bez zapisu w bazie.

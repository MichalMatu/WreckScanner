# Release Candidate Baseline

Ten dokument zamraza stan bazowy przed przejsciem na produkcyjna baze danych.
Jest punktem odniesienia dla migracji JSON -> DB, testow E2E i finalnego tagu
release candidate.

## Cel

Domknac WreckScanner jako produkcyjny release candidate:

- baza danych zgodna z modelem zdjec terenowych,
- zdjecia pozostaja bezpiecznymi plikami na dysku,
- raporty ZIP/PDF i cropy mapy sa jednorazowym wynikiem pobrania,
- mapa, raporty i prywatnosc sa potwierdzone testami,
- backup, restore, migracja i deploy sa opisane w dokumentacji.

## Baseline danych

Stan zapisany 2026-07-04 po zielonym `./scripts/check.sh`.

- commit bazowy: `a91f5b89568e8cc1e289291f50626d03acdc44ae`
- restic snapshot: `4aaaca53`
- snapshot time: `2026-07-04T08:22:13+02:00`
- backup repo: `.backups/wreckscanner-restic`
- backup password file: `.restic_password`
- status diagnostyki danych: `ok`
- zdjecia terenowe: `270`
- typy zdjec: `vehicle=240`, `infrastructure=29`, `smoke=1`
- nieznane typy zdjec: `0`
- zgloszenia prywatnosci: `0`
- prywatne oryginaly: `1142360401` bajtow
- publiczne kopie: `719882982` bajtow
- publiczne miniatury: `6873793` bajtow
- osierocone katalogi/pliki: `0/0`
- problemy diagnostyki: `0 error`, `0 warning`, `0 info`

Zakres snapshotu:

- `zdjecia_terenowe/`
- `prywatne_zdjecia/`
- `settings.json`
- `analiza/data_diagnostics.json`

## Podgole domkniecia

1. Zamrozenie stanu bazowego: backup, zielony check, baseline licznikow.
2. Kontrakt bazy: SQLite/WAL, migracje i twardy zakaz tabel dla raportow,
   cropow oraz starych spraw.
3. Migracja JSON -> DB: idempotentna, bez kasowania zdjec, z walidacja liczby
   rekordow i sciezek plikow.
4. Runtime na DB: `field_photos`, `settings` i `privacy_requests` czytane oraz
   zapisywane przez warstwe storage, JSON tylko jako import/export/backup.
5. E2E mapa + raport: upload, review, widocznosc na mapie, ZIP/PDF z
   fotografiami i tymczasowymi cropami mapy.
6. Prywatnosc, retencja i bezpieczenstwo: tokeny bez wyciekow, retencja
   oryginalow, backup/restore i konfiguracja sekretow.
7. Release candidate: pelny check, smoke HTTP, diagnostyka z plikami,
   dokumentacja deployu i tag `v1.0.0-rc1`.

## Bramka przed migracja DB

Przed uruchomieniem migracji DB wymagane sa:

```bash
./scripts/check.sh
./.venv/bin/python scripts/backup_data.py snapshots \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password
./.venv/bin/python scripts/backup_data.py check \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password
```

Migracja nie moze usuwac ani przenosic plikow z `zdjecia_terenowe/` i
`prywatne_zdjecia/`. Baza ma przechowywac metadane oraz sciezki do istniejacych
plikow.

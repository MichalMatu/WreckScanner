# WreckScanner

WreckScanner to lokalna aplikacja mapowa do dokumentowania pojazdow zalegajacych w przestrzeni publicznej. Wynik aplikacji jest materialem pomocniczym do weryfikacji, a nie decyzja o stanie prawnym pojazdu.

Aktualne wydanie: `v2.0`.

Status projektu: wersja utrzymaniowa. Repo zostaje odchudzone do kodu, testow i podstawowej dokumentacji potrzebnej do uruchomienia, backupu i pozniejszego serwisu.

## Start

```bash
cd /home/test/Desktop/WreckScanner
source .venv/bin/activate
./.venv/bin/python server.py
```

Aplikacja dziala pod:

```text
http://localhost:8000
```

W tym workspace serwer ma watcher autostartu. Przy pracy z dzialajaca aplikacja ubij aktualny proces `server.py` i poczekaj, az watcher podniesie nowy proces. Szczegoly sa w [docs/START.md](docs/START.md).

## Zakres

- mapa Leaflet z podkladami `POL`, `OSM` oraz rocznikami Wroclawia `2020-2025`,
- skan malego obszaru Wroclawia modelem YOLO OBB,
- reczne sprawy pojazdow z pakietami ZIP/PDF i publicznym `index.html`,
- zdjecia terenowe z kolejka zatwierdzania, anonimizacja i publicznymi kopiami bez EXIF,
- panel administratora dla zdjec, spraw, zgloszen prywatnosci, cache GeoTIFF i widocznosci warstw,
- warstwy dzialek KIEG/EGiB oraz nawierzchni OSM/Overpass,
- lokalny backup danych przez `restic`.

## Prywatnosc

Publiczne API zwraca tylko `public_image` i `public_thumb`; nie zwraca lokalnych sciezek ani prywatnych oryginalow. Oryginaly sa dostepne tylko przez endpointy administracyjne. Publiczne kopie zdjec sa publikowane dopiero po review i anonimizacji.

Haslo administratora pochodzi z `WRECKSCANNER_ADMIN_PASSWORD` albo z lokalnego pliku `.admin_password`. Plik jest ignorowany przez Git.

## Dokumentacja

- [docs/START.md](docs/START.md) - uruchamianie, zatrzymanie, smoke test i haslo administratora.
- [docs/BACKUP.md](docs/BACKUP.md) - lokalny backup i restore danych.

## Lokalne Dane

Te katalogi i pliki sa lokalna baza aplikacji albo cache i nie powinny trafic do repozytorium:

- `dane_dla_AI/` - pobrane ortofotomapy, metadane i cache GeoTIFF,
- `analiza/` - raporty analizy, miniatury, overlay, `candidates.json`, `run_log.json`,
- `zidentyfikowane_wraki/` - zapisane sprawy pojazdow,
- `zdjecia_terenowe/` - rekordy zdjec terenowych i publiczne pochodne,
- `prywatne_zdjecia/` - prywatne oryginaly zdjec,
- `prywatne_zgloszenia/` - prywatne pakiety zgloszen,
- `zgloszenia_prywatnosci/` - kolejka wnioskow o usuniecie, korekte lub anonimizacje,
- `settings.json` - lokalne ustawienia aplikacji,
- `.cache/` i `.backups/` - cache oraz lokalne repozytorium backupu.

## Kontrole

```bash
scripts/check.sh
make smoke
```

`scripts/check.sh` uruchamia compile, Ruff, testy, frontend lint, diagnostyki i `git diff --check`. `make smoke` sprawdza dzialajacy serwer.

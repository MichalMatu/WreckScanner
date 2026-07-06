# IleStoi.pl

IleStoi.pl to lokalna aplikacja mapowa do dokumentowania pojazdow zalegajacych w przestrzeni publicznej. Wynik aplikacji jest materialem pomocniczym do weryfikacji, a nie decyzja o stanie prawnym pojazdu.

Aktualne wydanie: `v3.1`.

Status projektu: wersja utrzymaniowa. Repo zostaje odchudzone do kodu, testow i podstawowej dokumentacji potrzebnej do uruchomienia, backupu i pozniejszego serwisu.

## Start

```bash
cd /home/test/Desktop/WreckScanner
source .venv/bin/activate
./.venv/bin/python server.py
```

Aplikacja dziala pod:

```text
http://127.0.0.1:8001
```

W tym workspace serwer ma watcher autostartu. Przy pracy z dzialajaca aplikacja ubij aktualny proces `server.py` i poczekaj, az watcher podniesie nowy proces. Szczegoly sa w [docs/START.md](docs/START.md).

## Zakres

- mapa Leaflet z podkladami `POL`, `OSM` oraz rocznikami Wroclawia `2020-2025`,
- zdjecia terenowe w SQLite z typem obserwacji, lokalizacja, kolejka zatwierdzania, anonimizacja i publicznymi kopiami bez EXIF,
- warstwa pojazdow budowana z zatwierdzonych zdjec terenowych, z recznym statusem OC/UFG dla grupy wraku,
- automatyczne miniatury historyczne pobierane z WMS podczas generowania zgloszenia,
- pakiety ZIP/PDF generowane na zadanie z wybranych zdjec terenowych, bez zapisu stalego rekordu sprawy,
- panel administratora dla zdjec, zgloszen prywatnosci, retencji oryginalow i widocznosci warstw,
- warstwa dzialek KIEG/EGiB,
- lokalny backup danych przez `restic`.

## Prywatnosc

Publiczne API zwraca tylko `public_image` i `public_thumb`; nie zwraca lokalnych sciezek ani prywatnych oryginalow. Oryginaly sa dostepne tylko przez endpointy administracyjne. Publiczne kopie zdjec sa publikowane dopiero po review i anonimizacji.

Haslo administratora pochodzi z `WRECKSCANNER_ADMIN_PASSWORD` albo z lokalnego pliku `.admin_password`. Plik jest ignorowany przez Git.

## Dokumentacja

- [docs/START.md](docs/START.md) - uruchamianie, zatrzymanie, smoke test i haslo administratora.
- [docs/CURRENT_MODEL.md](docs/CURRENT_MODEL.md) - aktualny model danych, endpointy i audyt braku starych artefaktow.
- [docs/PUBLIC_RUNTIME.md](docs/PUBLIC_RUNTIME.md) - porty publicznych uslug i konfiguracja Cloudflare Tunnel.
- [docs/BACKUP.md](docs/BACKUP.md) - lokalny backup i restore danych.
- [docs/DEPLOY.md](docs/DEPLOY.md) - produkcyjny deploy, sekrety, systemd i rollback.

## Git Flow

- `main` jest linia release-only: jeden commit `Release vX.Y baseline` na wydanie i pasujacy tag, np. `v3.1`.
- `work/dirty` jest galezia robocza do codziennego rozwoju, poprawek i eksperymentow.
- Po weryfikacji stan z `work/dirty` trafia na `main` jako squash release baseline.

## Lokalne Dane

Te katalogi i pliki sa lokalna baza aplikacji albo cache i nie powinny trafic do repozytorium:

- `analiza/` - lokalne raporty diagnostyczne uruchamiane przez `scripts/check.sh`,
- `wreckscanner.sqlite3` - aktywny stan aplikacji: zdjecia terenowe, ustawienia i zgloszenia prywatnosci,
- `zdjecia_terenowe/` - publiczne pochodne zdjec terenowych i katalogi plikow,
- `prywatne_zdjecia/` - prywatne oryginaly zdjec,
- `zgloszenia_prywatnosci/` i `settings.json` - historyczny/importowy format JSON,
- `.cache/` i `.backups/` - cache oraz lokalne repozytorium backupu.

`prywatne_zgloszenia/` to wycofany katalog starych, trwale zapisanych pakietow
raportow. Nie jest aktywnym storage aplikacji; `scripts/diagnose_data.py` traktuje
jego obecnosc jako blad danych przed release candidate.

## Kontrole

```bash
scripts/check.sh
make smoke
make e2e-report
```

`scripts/check.sh` uruchamia compile, Ruff, testy, frontend lint, diagnostyki i `git diff --check`. `make smoke` sprawdza dzialajacy serwer, a `make e2e-report` wykonuje przeplyw upload -> review -> mapa -> raport ZIP/PDF z OC/UFG.

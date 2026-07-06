# Backup

Dane aplikacji to baza SQLite oraz pliki zdjec w katalogach projektu. Lokalny
backup uzywa `restic`.

## Pliki

- repozytorium backupu: `.backups/wreckscanner-restic`
- haslo backupu: `.restic_password`

`.restic_password` jest ignorowany przez Git. Bez niego nie odtworzysz snapshotow, wiec trzymaj kopie poza jedyna kopia repozytorium backupu. Nie nadpisuj go przy rotacji `.admin_password`, chyba ze swiadomie zmieniasz haslo backupu.

## Zakres

Backup obejmuje dane uzytkowe:

- `zdjecia_terenowe/`
- `prywatne_zdjecia/`
- `wreckscanner.sqlite3`, `wreckscanner.sqlite3-wal`, `wreckscanner.sqlite3-shm`,
  jesli istnieja po migracji DB
- `zgloszenia_prywatnosci/` i `settings.json`, jesli istnieja jako material
  importowy albo historyczny
- `analiza/data_diagnostics.json`, jesli istnieje

Backup pomija zaleznosci, cache, `.backups/` i raporty wygenerowane do jednorazowego pobrania.

## Snapshot ZIP z menu `make`

Domyslne `make` otwiera menu z numerami. Opcja `6` zatrzymuje serwer na czas
kopii i tworzy pelny snapshot ZIP w katalogu `kopie_zapasowe/`, a opcja `7`
odtwarza dane z wybranego ZIP-a.

Snapshot ZIP zawiera pelny stan danych potrzebny do odtworzenia dzialajacej
instalacji na tym samym kodzie aplikacji:

- `wreckscanner.sqlite3` jako spojny snapshot SQLite,
- `zdjecia_terenowe/`,
- `prywatne_zdjecia/`,
- `zgloszenia_prywatnosci/`, jesli istnieje,
- `settings.json`, jesli istnieje,
- `analiza/data_diagnostics.json`,
- `.admin_password` i `.restic_password`, jesli istnieja,
- `manifest.json` z lista wpisow, rozmiarami i hashami SHA256 plikow.

ZIP nie jest szyfrowany. Poniewaz zawiera hasla i prywatne zdjecia, trzymaj go
poza repozytorium i poza jedyna karta SD Raspberry Pi, np. na dysku USB, NAS albo
innym komputerze. Katalog `kopie_zapasowe/` jest ignorowany przez Git.

Komendy bez menu:

```bash
make backup-data
make list-backups
make restore-data BACKUP=kopie_zapasowe/wreckscanner-snapshot-YYYYMMDD_HHMMSS.zip
```

Backup i odtwarzanie pamietaja poprzedni stan autostartu. Jesli autostart byl
wylaczony przed operacja, po operacji pozostaje wylaczony.

Odtwarzanie ZIP-a:

1. wylacza autostart i zatrzymuje `server.py`,
2. sprawdza archiwum i integralnosc bazy SQLite,
3. przenosi obecny stan danych do `kopie_zapasowe/przed_odtworzeniem/`,
4. podmienia dane z archiwum,
5. wlacza serwer ponownie.

## Komendy

```bash
cd /home/test/Desktop/WreckScanner

./.venv/bin/python scripts/backup_data.py run \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password

./.venv/bin/python scripts/backup_data.py snapshots \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password

./.venv/bin/python scripts/backup_data.py check \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password

mkdir -p /tmp/wreckscanner-restore-test
RESTIC_REPOSITORY=/home/test/Desktop/WreckScanner/.backups/wreckscanner-restic \
RESTIC_PASSWORD_FILE=/home/test/Desktop/WreckScanner/.restic_password \
restic restore latest --target /tmp/wreckscanner-restore-test

./.venv/bin/python scripts/diagnose_data.py --strict \
  --field-photos-dir /tmp/wreckscanner-restore-test/zdjecia_terenowe \
  --private-photos-dir /tmp/wreckscanner-restore-test/prywatne_zdjecia

./.venv/bin/python scripts/migrate_json_to_db.py \
  --root-dir /tmp/wreckscanner-restore-test \
  --database /tmp/wreckscanner-restore-test/wreckscanner.sqlite3 \
  --validate-only
```

`restic restore` odtwarza sciezki backupu bez prefiksu katalogu projektu, czyli
po powyzszej komendzie dane leza bezposrednio w
`/tmp/wreckscanner-restore-test/zdjecia_terenowe`,
`/tmp/wreckscanner-restore-test/prywatne_zdjecia` i
`/tmp/wreckscanner-restore-test/wreckscanner.sqlite3`.

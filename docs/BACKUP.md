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

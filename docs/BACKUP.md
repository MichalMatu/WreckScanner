# Backup

Dane aplikacji sa plikami w katalogach projektu. Lokalny backup uzywa `restic`.

## Pliki

- repozytorium backupu: `.backups/wreckscanner-restic`
- haslo backupu: `.restic_password`

`.restic_password` jest ignorowany przez Git. Bez niego nie odtworzysz snapshotow, wiec trzymaj kopie poza jedyna kopia repozytorium backupu. Nie nadpisuj go przy rotacji `.admin_password`, chyba ze swiadomie zmieniasz haslo backupu.

## Zakres

Backup obejmuje dane uzytkowe:

- `zidentyfikowane_wraki/`
- `zdjecia_terenowe/`
- `prywatne_zdjecia/`
- `zgloszenia_prywatnosci/`, jesli istnieje
- `settings.json`, jesli istnieje
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
```

# Deploy Produkcyjny

Ten runbook opisuje lokalny deploy IleStoi.pl na Raspberry Pi za tunelem
Cloudflare. Aktywnym stanem aplikacji jest SQLite oraz pliki zdjec na dysku.

## Sekrety i zmienne

Minimalny zestaw produkcyjny:

```bash
WRECKSCANNER_HOST=127.0.0.1
WRECKSCANNER_PORT=8001
WRECKSCANNER_ADMIN_PASSWORD=...
WRECKSCANNER_ADMIN_SESSION_SECRET=...
WRECKSCANNER_ADMIN_COOKIE_SECURE=1
WRECKSCANNER_CORS_ALLOWED_ORIGINS=https://wreckscanner.pl,https://ilestoi.pl,https://dlugostoi.pl
WRECKSCANNER_TRUSTED_PROXY_ADDRESSES=127.0.0.1,::1
WRECKSCANNER_PHOTO_RETENTION_AUTORUN=1
```

`WRECKSCANNER_ADMIN_SESSION_SECRET` musi byc staly miedzy restartami. Gdy go
brakuje, aplikacja wygeneruje losowy sekret procesu, co jest wygodne lokalnie,
ale uniewaznia sesje admina po kazdym restarcie.

`.admin_password` jest dopuszczalny lokalnie, ale w usludze systemd wygodniej
uzyc `EnvironmentFile` z `WRECKSCANNER_ADMIN_PASSWORD`. Nie commituj zadnego
pliku z sekretami.

## Systemd

Przyklad jednostki:

```ini
[Unit]
Description=IleStoi.pl
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/home/test/Desktop/WreckScanner
EnvironmentFile=/home/test/Desktop/WreckScanner/.env.production
ExecStart=/home/test/Desktop/WreckScanner/.venv/bin/python /home/test/Desktop/WreckScanner/server.py
Restart=on-failure
RestartSec=3
User=test

[Install]
WantedBy=multi-user.target
```

Po zmianie jednostki:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now wreckscanner.service
systemctl status wreckscanner.service --no-pager
```

Cloudflare Tunnel i publiczne hosty sa opisane w
[PUBLIC_RUNTIME.md](PUBLIC_RUNTIME.md).

## Przed Deployem

```bash
git status --short --branch
./scripts/check.sh
./.venv/bin/python scripts/diagnose_data.py --strict
./.venv/bin/python scripts/migrate_json_to_db.py --validate-only
./.venv/bin/python scripts/backup_data.py run \
  --repo .backups/wreckscanner-restic \
  --password-file .restic_password
```

Przed pierwszym publicznym wdrozeniem wykonaj tez probe restore wedlug
[BACKUP.md](BACKUP.md).

## Po Deployu

```bash
sudo systemctl restart wreckscanner.service
curl -fsS http://127.0.0.1:8001/api/health
make smoke
make e2e-report
```

`make e2e-report` wymaga dzialajacego WMS i Chromium. Test tworzy tymczasowe
zdjecie, generuje raport ZIP/PDF z cropami mapy i statusem OC/UFG, a potem usuwa
testowe pliki po sobie.

## Rollback

1. Zatrzymaj usluge: `sudo systemctl stop wreckscanner.service`.
2. Odtworz snapshot restic do katalogu tymczasowego wedlug [BACKUP.md](BACKUP.md).
3. Zweryfikuj odtworzone dane przez `diagnose_data.py --strict` i
   `migrate_json_to_db.py --validate-only`.
4. Po potwierdzeniu zamien `wreckscanner.sqlite3`, `zdjecia_terenowe/` i
   `prywatne_zdjecia/` na odtworzone wersje.
5. Uruchom usluge: `sudo systemctl start wreckscanner.service`.
6. Wykonaj `make smoke` i `make e2e-report`.

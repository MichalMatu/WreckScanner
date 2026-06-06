# Start I Utrzymanie

## Uruchomienie

```bash
cd /home/test/Desktop/WreckScanner
source .venv/bin/activate
./.venv/bin/python server.py
```

Adres lokalny:

```text
http://localhost:8000
```

## Autostart

W tym workspace serwer ma watcher autostartu. Nie uruchamiaj drugiej kopii recznie, jesli proces juz dziala.

Sprawdzenie:

```bash
pgrep -af "/home/test/Desktop/WreckScanner/server.py"
```

Restart:

```bash
make restart
```

Zatrzymanie:

```bash
make stop
```

Wylaczenie autostartu:

```bash
make disable-autostart
```

Ponowne wlaczenie:

```bash
make enable-autostart
```

## Haslo Administratora

Haslo pochodzi z `WRECKSCANNER_ADMIN_PASSWORD` albo z lokalnego pliku `.admin_password`. Zmienna srodowiskowa ma pierwszenstwo przed plikiem `.admin_password`.

Utworzenie lokalnego hasla:

```bash
openssl rand -base64 24 > .admin_password
chmod 600 .admin_password
```

Po zmianie hasla stare sesje administratora przestaja przechodzic walidacje.

## Kontrole

Pelny lokalny zestaw:

```bash
scripts/check.sh
```

Smoke test dzialajacego serwera:

```bash
make smoke
```

Szybki health check:

```bash
curl -fsS http://localhost:8000/api/health
```

## Backup

Backup i restore opisuje [BACKUP.md](BACKUP.md). Pliku `.restic_password` nie nadpisuj przy rotacji hasla administratora, chyba ze swiadomie zmieniasz haslo repozytorium backupu.

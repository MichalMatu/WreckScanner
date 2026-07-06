.DEFAULT_GOAL := menu

.PHONY: menu help start stop restart status logs check test lint smoke e2e-report health wait-server autostart autostart-start autostart-stop autostart-status serwerstart serwerstop backup-data restore-data list-backups backup-db restore-db

PYTHON ?= $(shell if [ -x ./.venv/bin/python ]; then printf './.venv/bin/python'; elif command -v python3 >/dev/null 2>&1; then command -v python3; else command -v python; fi)
HOST ?= 127.0.0.1
PORT ?= 8001
SERVER_URL := http://$(HOST):$(PORT)
BACKUP_DIR ?= kopie_zapasowe
SERVER_PATTERN := [p]ython[^[:space:]]*[[:space:]].*$(CURDIR)/server\.py([[:space:]]|$$)
SERVER_WAIT_SECONDS ?= 8
SERVER_AUTOSTART_WAIT_SECONDS ?= 3
SERVER_LOG ?= .dev/server.log
SERVER_PID_FILE ?= .dev/server.pid
AUTOSTART_DISABLED_FILE ?= .dev/server.autostart.disabled
AUTOSTART_ACTION := $(firstword $(filter start stop status,$(MAKECMDGOALS)))

menu:
	@printf '%s\n' \
		'WreckScanner - menu:' \
		'' \
		'  1. Status serwera' \
		'  2. Restart serwera' \
		'  3. Zatrzymaj serwer' \
		'  4. Uruchom serwer' \
		'  5. Pelny check aplikacji' \
		'  6. Stworz pelna kopie zapasowa ZIP' \
		'  7. Odtworz dane z kopii ZIP' \
		'  8. Pokaz lokalne kopie ZIP' \
		'  9. Pokaz logi' \
		'  0. Wyjscie' \
		''
	@printf 'Wybor: '; \
	read choice; \
	case "$$choice" in \
		1) $(MAKE) status ;; \
		2) $(MAKE) restart ;; \
		3) $(MAKE) serwerstop ;; \
		4) $(MAKE) serwerstart ;; \
		5) $(MAKE) check ;; \
		6) $(MAKE) backup-data ;; \
		7) printf 'Sciezka do ZIP: '; read backup; \
			if [ -z "$$backup" ]; then echo 'Brak sciezki do ZIP.'; exit 2; fi; \
			$(MAKE) restore-data BACKUP="$$backup" ;; \
		8) $(MAKE) list-backups ;; \
		9) $(MAKE) logs ;; \
		0) exit 0 ;; \
		*) echo 'Nieznany wybor.'; exit 2 ;; \
	esac

help:
	@printf '%s\n' \
		'WreckScanner - komendy:' \
		'' \
		'Serwer:'
	@printf '  %-24s %s\n' \
		'make start' 'status procesu' \
		'make stop' 'zatrzymaj server.py' \
		'make restart' 'restart przez watcher' \
		'make serwerstop' 'wylacz autostart + stop' \
		'make serwerstart' 'wlacz autostart + start' \
		'make autostart-status' 'status autostartu'
	@printf '%s\n' '' 'Diagnostyka:'
	@printf '  %-24s %s\n' \
		'make status' 'PID + health' \
		'make logs' 'ostatnie logi' \
		'make check' 'pelny check' \
		'make test' 'testy' \
		'make lint' 'lint + format' \
		'make smoke' 'runtime smoke dzialajacego serwera' \
		'make e2e-report' 'upload/review/map/raport ZIP+PDF dzialajacego serwera' \
		'make health' 'alias status'
	@printf '%s\n' '' 'Backup:'
	@printf '  %-36s %s\n' \
		'make backup-data' 'pelny snapshot ZIP, zatrzymuje serwer na czas kopii' \
		'make restore-data BACKUP=plik.zip' 'odtworz pelny snapshot ZIP' \
		'make list-backups' 'pokaz lokalne kopie ZIP'

start:
	@if pgrep -af '$(SERVER_PATTERN)' >/dev/null; then \
		echo 'server.py juz dziala:'; \
		pgrep -af '$(SERVER_PATTERN)'; \
	elif [ -f "$(AUTOSTART_DISABLED_FILE)" ]; then \
		echo 'server.py nie dziala, bo autostart jest wylaczony:'; \
		echo '$(AUTOSTART_DISABLED_FILE)'; \
		echo 'Aby wlaczyc ponownie: make serwerstart'; \
	else \
		echo 'server.py nie dziala.'; \
		echo 'W tym srodowisku proces powinien podniesc autostart watcher; make nie uruchamia drugiej kopii serwera.'; \
		echo 'Jesli watcher jest wylaczony, uruchom recznie tylko tymczasowo: $(PYTHON) server.py'; \
	fi

stop:
	@pids="$$(pgrep -f '$(SERVER_PATTERN)' || true)"; \
	if [ -z "$$pids" ]; then \
		echo 'server.py nie dziala.'; \
	else \
		echo "Zatrzymuje server.py: $$pids"; \
		kill $$pids; \
	fi
	@rm -f "$(SERVER_PID_FILE)"

restart: stop
	@$(MAKE) wait-server

wait-server:
	@i=0; \
	while [ "$$i" -lt "$(SERVER_WAIT_SECONDS)" ]; do \
		if pgrep -af '$(SERVER_PATTERN)' >/dev/null; then \
			if command -v curl >/dev/null 2>&1; then \
				if curl -fsS "$(SERVER_URL)/api/health" >/dev/null 2>&1; then \
					echo 'server.py dziala:'; \
					pgrep -af '$(SERVER_PATTERN)'; \
					echo 'Health OK'; \
					exit 0; \
				fi; \
			else \
				echo 'server.py dziala:'; \
				pgrep -af '$(SERVER_PATTERN)'; \
				exit 0; \
			fi; \
		fi; \
		i=$$((i + 1)); \
		sleep 1; \
	done; \
	echo 'Autostart nie podniosl zdrowego server.py w ciagu $(SERVER_WAIT_SECONDS)s.'; \
	echo 'Sprawdz watcher albo uruchom tymczasowo: $(PYTHON) server.py'; \
	exit 1

autostart:
	@if [ "$(AUTOSTART_ACTION)" = "stop" ]; then \
		$(MAKE) autostart-stop; \
	elif [ "$(AUTOSTART_ACTION)" = "start" ]; then \
		$(MAKE) autostart-start; \
	else \
		$(MAKE) autostart-status; \
	fi

autostart-stop:
	@mkdir -p "$(dir $(AUTOSTART_DISABLED_FILE))"
	@printf 'disabled\n' > "$(AUTOSTART_DISABLED_FILE)"
	@echo 'Autostart server.py wylaczony.'
	@$(MAKE) stop

autostart-start:
	@rm -f "$(AUTOSTART_DISABLED_FILE)"
	@mkdir -p "$(dir $(SERVER_LOG))"
	@if pgrep -af '$(SERVER_PATTERN)' >/dev/null; then \
		echo 'Autostart server.py wlaczony; server.py juz dziala:'; \
		pgrep -af '$(SERVER_PATTERN)'; \
	else \
		echo 'Autostart server.py wlaczony. Czekam chwile na watcher.'; \
		if $(MAKE) SERVER_WAIT_SECONDS=$(SERVER_AUTOSTART_WAIT_SECONDS) wait-server; then \
			exit 0; \
		fi; \
		echo 'Watcher nie podniosl server.py, uruchamiam server.py w tle.'; \
		WRECKSCANNER_HOST="$(HOST)" WRECKSCANNER_PORT="$(PORT)" nohup "$(PYTHON)" "$(CURDIR)/server.py" >> "$(SERVER_LOG)" 2>&1 & \
		echo $$! > "$(SERVER_PID_FILE)"; \
		$(MAKE) wait-server; \
	fi

autostart-status:
	@if [ -f "$(AUTOSTART_DISABLED_FILE)" ]; then \
		echo 'Autostart server.py: wylaczony'; \
		echo 'Blokada:' "$(AUTOSTART_DISABLED_FILE)"; \
	else \
		echo 'Autostart server.py: wlaczony'; \
	fi
	@$(MAKE) status

serwerstop: autostart-stop

serwerstart: autostart-start

status:
	@printf '%s\n' 'Procesy server.py:'
	@pgrep -af '$(SERVER_PATTERN)' || true
	@printf '\n%s\n' 'Health:'
	@if command -v curl >/dev/null 2>&1; then curl -fsS "$(SERVER_URL)/api/health" || true; else echo 'curl niedostepny'; fi
	@printf '\n'

logs:
	@if [ -f "$(SERVER_LOG)" ]; then \
		tail -n 80 "$(SERVER_LOG)"; \
	else \
		echo 'Brak $(SERVER_LOG). Serwer prawdopodobnie dziala z autostartu.'; \
	fi

check:
	@./scripts/check.sh

test:
	@"$(PYTHON)" -m unittest discover -s tests

lint:
	@"$(PYTHON)" -m ruff check app core scripts tests server.py
	@"$(PYTHON)" -m ruff format --check app core scripts tests server.py
	@if [ -x ./node_modules/.bin/eslint ]; then \
		./node_modules/.bin/eslint web/*.js; \
	elif command -v npm >/dev/null 2>&1; then \
		npm run lint:web; \
	else \
		echo 'skip: npm/eslint niedostepne, pomijam lint JS'; \
	fi

smoke:
	@"$(PYTHON)" scripts/smoke_runtime.py --base-url "$(SERVER_URL)"

e2e-report:
	@"$(PYTHON)" scripts/e2e_field_photo_report.py --base-url "$(SERVER_URL)"

health: status

backup-data:
	@was_disabled=0; \
	if [ -f "$(AUTOSTART_DISABLED_FILE)" ]; then was_disabled=1; fi; \
	status=0; \
	$(MAKE) autostart-stop || status=$$?; \
	if [ "$$status" -eq 0 ]; then \
		"$(PYTHON)" scripts/backup_data.py zip --root-dir "$(CURDIR)" --output-dir "$(BACKUP_DIR)" || status=$$?; \
	fi; \
	if [ "$$was_disabled" -eq 0 ]; then \
		$(MAKE) autostart-start || true; \
	else \
		echo 'Autostart byl wylaczony przed backupem; zostawiam wylaczony.'; \
	fi; \
	exit "$$status"

restore-data:
	@if [ -z "$(BACKUP)" ]; then \
		echo 'Podaj plik kopii: make restore-data BACKUP=kopie_zapasowe/plik.zip'; \
		exit 2; \
	fi
	@was_disabled=0; \
	if [ -f "$(AUTOSTART_DISABLED_FILE)" ]; then was_disabled=1; fi; \
	status=0; \
	$(MAKE) autostart-stop || status=$$?; \
	if [ "$$status" -eq 0 ]; then \
		"$(PYTHON)" scripts/backup_data.py restore-zip --root-dir "$(CURDIR)" --archive "$(BACKUP)" || status=$$?; \
	fi; \
	if [ "$$was_disabled" -eq 0 ]; then \
		$(MAKE) autostart-start || true; \
	else \
		echo 'Autostart byl wylaczony przed odtwarzaniem; zostawiam wylaczony.'; \
	fi; \
	exit "$$status"

list-backups:
	@"$(PYTHON)" scripts/backup_data.py list-zips --root-dir "$(CURDIR)" --output-dir "$(BACKUP_DIR)"

backup-db: backup-data

restore-db: restore-data

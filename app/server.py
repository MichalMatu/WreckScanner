import errno
import sys

from app import config
from app.http import retention as http_retention
from app.http import server as http_server
from core import config as core_config
from core.runtime import configure_process_encoding, harden_private_runtime_storage

configure_process_encoding()


def main() -> None:
    harden_private_runtime_storage(
        database_path=config.ROOT_DIR / core_config.DATABASE_PATH,
        private_photos_dir=config.ROOT_DIR / core_config.PRIVATE_PHOTOS_DIR,
    )
    try:
        srv = http_server.ReusableHTTPServer((config.HOST, config.PORT), http_server.Handler)
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, 48):
            print(
                f"❌ Port {config.PORT} jest już zajęty. Zamknij poprzedni serwer albo sprawdź: lsof -nP -iTCP:{config.PORT} -sTCP:LISTEN"
            )
            sys.exit(1)
        if e.errno in (errno.EACCES, errno.EPERM):
            print(f"❌ Nie udało się otworzyć portu {config.PORT}: brak uprawnienia procesu.")
            print("   Wyjdź z obcego virtualenv, np. `deactivate`, i uruchom ponownie: python3 server.py")
            sys.exit(1)
        raise
    print(f"🚀 Serwer działa na http://{config.HOST}:{config.PORT}")
    print("   Otwórz tę stronę w przeglądarce.")
    if http_retention.start_scheduler():
        print("   Retencja prywatnych oryginałów: automatycznie przy starcie i potem co 24h.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Serwer zatrzymany.")


if __name__ == "__main__":
    main()

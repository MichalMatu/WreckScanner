from pathlib import Path

AUTOSTART_DISABLED_FILE = Path(__file__).resolve().parent / ".dev" / "server.autostart.disabled"


def main() -> None:
    if AUTOSTART_DISABLED_FILE.exists():
        print(f"server.py nie startuje: autostart wylaczony ({AUTOSTART_DISABLED_FILE}).")
        return

    from app.server import main as app_main

    app_main()


if __name__ == "__main__":
    main()

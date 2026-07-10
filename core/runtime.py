from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path

TEXT_ENCODING = "utf-8"
TEXT_ERRORS = "replace"
PYTHON_IO_ENCODING = f"{TEXT_ENCODING}:{TEXT_ERRORS}"
PRIVATE_RUNTIME_UMASK = 0o077


def configure_process_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with suppress(TypeError, ValueError):
            reconfigure(encoding=TEXT_ENCODING, errors=TEXT_ERRORS)
    os.environ["PYTHONIOENCODING"] = PYTHON_IO_ENCODING


def harden_private_runtime_storage(*, database_path: Path, private_photos_dir: Path) -> None:
    """Keep newly created and existing private runtime state owner-only."""

    os.umask(PRIVATE_RUNTIME_UMASK)
    if private_photos_dir.is_symlink():
        raise RuntimeError("Katalog prywatnych zdjęć nie może być dowiązaniem symbolicznym.")
    private_photos_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_photos_dir.chmod(0o700)
    for path in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise RuntimeError(f"Nieprawidłowy prywatny plik stanu: {path.name}")
            path.chmod(0o600)


def subprocess_text_kwargs() -> dict[str, str]:
    return {"encoding": TEXT_ENCODING, "errors": TEXT_ERRORS}

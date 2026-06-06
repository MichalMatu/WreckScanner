from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.json_io import write_json_atomic


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    write_json_atomic(path, payload)


def validate_wreck_id(wreck_id: str) -> str:
    if not re.fullmatch(r"wreck_-?\d+_-?\d+", wreck_id):
        raise ValueError("Nieprawidłowy identyfikator sprawy pojazdu.")
    return wreck_id


def record_dir_for(wreck_id: str, wrecks_dir: Path) -> Path:
    wreck_id = validate_wreck_id(wreck_id)
    root = wrecks_dir.resolve()
    record_dir = (wrecks_dir / wreck_id).resolve()
    if root != record_dir and root not in record_dir.parents:
        raise ValueError("Nieprawidłowa ścieżka sprawy pojazdu.")
    if not (record_dir / "record.json").exists():
        raise FileNotFoundError("Nie znaleziono zapisanej sprawy pojazdu.")
    return record_dir

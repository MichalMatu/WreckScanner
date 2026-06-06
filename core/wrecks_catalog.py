from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core import config
from core.geo import meters_between
from core.wrecks_migration import migrate_wreck_record
from core.wrecks_store import read_json, write_json


def load_records(wrecks_dir: Path) -> list[dict[str, Any]]:
    if not wrecks_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(wrecks_dir.glob("*/record.json")):
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and record.get("id"):
            if migrate_wreck_record(path.parent, record):
                write_json(path, record)
            records.append(record)
    return records


def find_existing_record(wrecks_dir: Path, lat: float, lon: float) -> tuple[dict[str, Any] | None, float | None]:
    best: dict[str, Any] | None = None
    best_dist: float | None = None
    for record in load_records(wrecks_dir):
        try:
            dist = meters_between(lat, lon, float(record["lat"]), float(record["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
        if dist <= config.WRECK_DEDUPE_M and (best_dist is None or dist < best_dist):
            best = record
            best_dist = dist
    return best, best_dist

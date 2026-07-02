from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from core import config
from core.config import DEFAULT_ENHANCEMENT_SETTINGS, EnhancementSettings
from core.json_io import write_json_atomic

SETTINGS_PATH = Path(__file__).resolve().parent.parent / config.SETTINGS_FILENAME
DEFAULT_PUBLIC_LAYERS: dict[str, bool] = {
    "saved_wrecks": True,
    "field_photo_vehicle": True,
    "field_photo_infrastructure": True,
    "field_photo_smoke": True,
    "field_photo_pending": True,
    "cadastral": True,
    "base_map_osm": True,
}
DEFAULT_PUBLIC_FEATURES: dict[str, bool] = {
    "manual_wrecks": True,
    "photo_uploads": True,
}

_ENHANCEMENT_LIMITS: dict[str, tuple[float, float]] = {
    "clahe_clip_limit": (0.1, 5.0),
    "clahe_tile_grid_size": (1, 32),
    "l_percentile_low": (0.0, 40.0),
    "l_percentile_high": (60.0, 100.0),
    "l_output_low": (0.0, 120.0),
    "l_output_high": (135.0, 255.0),
    "l_min_percentile_span": (1.0, 50.0),
    "decast_strength": (0.0, 1.0),
}


def enhancement_settings_to_dict(settings: EnhancementSettings) -> dict[str, Any]:
    return asdict(settings)


def enhancement_settings_from_dict(raw: Any) -> EnhancementSettings:
    defaults = enhancement_settings_to_dict(DEFAULT_ENHANCEMENT_SETTINGS)
    if not isinstance(raw, dict):
        return DEFAULT_ENHANCEMENT_SETTINGS

    data = defaults.copy()
    if "enabled" in raw:
        data["enabled"] = bool(raw["enabled"])

    for key, (min_value, max_value) in _ENHANCEMENT_LIMITS.items():
        if key not in raw:
            continue
        try:
            value = float(raw[key])
        except (TypeError, ValueError):
            continue
        value = max(min_value, min(max_value, value))
        data[key] = int(round(value)) if key == "clahe_tile_grid_size" else value

    if data["l_percentile_low"] >= data["l_percentile_high"]:
        data["l_percentile_low"] = defaults["l_percentile_low"]
        data["l_percentile_high"] = defaults["l_percentile_high"]
    if data["l_output_low"] >= data["l_output_high"]:
        data["l_output_low"] = defaults["l_output_low"]
        data["l_output_high"] = defaults["l_output_high"]

    return EnhancementSettings(**data)


def default_app_settings() -> dict[str, Any]:
    return {
        "enhancement": enhancement_settings_to_dict(DEFAULT_ENHANCEMENT_SETTINGS),
        "public_layers": DEFAULT_PUBLIC_LAYERS.copy(),
        "public_features": DEFAULT_PUBLIC_FEATURES.copy(),
    }


def public_layer_settings_from_dict(raw: Any) -> dict[str, bool]:
    settings = DEFAULT_PUBLIC_LAYERS.copy()
    if not isinstance(raw, dict):
        return settings

    for key in settings:
        if key in raw:
            settings[key] = bool(raw[key])
    return settings


def public_feature_settings_from_dict(raw: Any) -> dict[str, bool]:
    settings = DEFAULT_PUBLIC_FEATURES.copy()
    if not isinstance(raw, dict):
        return settings

    for key in settings:
        if key in raw:
            settings[key] = bool(raw[key])
    return settings


def load_app_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return default_app_settings()

    try:
        with SETTINGS_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_app_settings()

    if not isinstance(raw, dict):
        return default_app_settings()

    settings = default_app_settings()
    settings["enhancement"] = enhancement_settings_to_dict(enhancement_settings_from_dict(raw.get("enhancement")))
    settings["public_layers"] = public_layer_settings_from_dict(raw.get("public_layers"))
    settings["public_features"] = public_feature_settings_from_dict(raw.get("public_features"))
    return settings


def load_enhancement_settings() -> EnhancementSettings:
    return enhancement_settings_from_dict(load_app_settings().get("enhancement"))


def save_app_settings(raw: dict[str, Any]) -> dict[str, Any]:
    current = load_app_settings()
    if "enhancement" in raw:
        current["enhancement"] = enhancement_settings_to_dict(enhancement_settings_from_dict(raw["enhancement"]))
    if "public_layers" in raw:
        current["public_layers"] = public_layer_settings_from_dict(raw["public_layers"])
    if "public_features" in raw:
        current["public_features"] = public_feature_settings_from_dict(raw["public_features"])

    write_json_atomic(SETTINGS_PATH, current)

    return current

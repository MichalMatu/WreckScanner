from __future__ import annotations

import os
import time
from contextlib import suppress
from pathlib import Path

from core import reporter_crops, reporter_html, reporter_json, reporter_overlay
from core.models import Candidate, ImageItem


def clear_generated_files(*dirs: Path) -> None:
    for directory in dirs:
        if not directory.is_dir():
            continue
        for name in os.listdir(directory):
            if name.lower().endswith((".jpg", ".jpeg", ".png")):
                with suppress(OSError):
                    (directory / name).unlink()


def write_analysis_outputs(
    items: list[ImageItem],
    ref_item: ImageItem,
    candidates: list[Candidate],
    output_dir: Path,
    crops_dir: Path,
    overlay_dir: Path,
    img_w: int,
    img_h: int,
    eps_px: float,
    crop_px: int,
    lang: str = "pl",
) -> None:
    reporter_crops.save_candidate_crops(
        items, ref_item, candidates, crops_dir, output_dir / "crop_manifest.json", img_w, img_h, crop_px=crop_px
    )
    reporter_overlay.save_overlay(ref_item, candidates, overlay_dir / "scored_overlay.jpg", eps_px)
    reporter_json.save_candidates_json(candidates, output_dir / "candidates.json")
    asset_version = str(time.time_ns())
    reporter_html.render_report(
        items, candidates, output_dir / "report.html", asset_version, img_w=img_w, img_h=img_h, lang=lang
    )

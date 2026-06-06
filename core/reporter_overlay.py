from __future__ import annotations

from pathlib import Path

import cv2

from core.models import Candidate, ImageItem
from core.vision import aligned_image


def save_overlay(ref_item: ImageItem, candidates: list[Candidate], overlay_path: Path, eps_px: float) -> None:
    overlay = aligned_image(ref_item).copy()
    for candidate in candidates:
        cx, cy = int(candidate.cx), int(candidate.cy)
        color = (0, 255, 0) if candidate.score > 0.8 else (0, 200, 255) if candidate.score > 0.5 else (0, 0, 255)
        # The circle is visual context; Leaflet/report pins carry exact candidate numbering.
        cv2.circle(overlay, (cx, cy), int(eps_px), color, 1, lineType=cv2.LINE_AA)
    cv2.imwrite(str(overlay_path), overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import cv2

from core.config import (
    DETECTION_CROP_MAX_DIST_M,
    DETECTION_CROP_MIN_MATCH_SCORE,
    LOCAL_CROP_ALIGN_CONTEXT_FACTOR,
    LOCAL_CROP_ALIGN_MAX_SHIFT_FACTOR,
    LOCAL_CROP_ALIGN_MIN_ACCEPTED_SHIFT_PX,
    LOCAL_CROP_ALIGN_MIN_PX,
    LOCAL_CROP_ALIGN_MIN_RESPONSE,
    LOCAL_CROP_ALIGN_REFERENCE_MAX_SHIFT_FACTOR,
    LOCAL_CROP_ALIGN_REFERENCE_MIN_RESPONSE,
    LOCAL_CROP_ALIGN_WEAK_DET_MIN_RESPONSE,
    REVIEW_JPEG_QUALITY,
)
from core.models import Candidate, ImageItem, Observation
from core.vision import aligned_image, alignment_image, crop_bounds


def local_aligned_crop_center(
    ref_img,
    img,
    candidate: Candidate,
    img_w: int,
    img_h: int,
    crop_px: int,
    min_response: float = LOCAL_CROP_ALIGN_MIN_RESPONSE,
    max_shift_factor: float = LOCAL_CROP_ALIGN_MAX_SHIFT_FACTOR,
) -> tuple[float, float, dict[str, Any] | None]:
    context_px = int(max(LOCAL_CROP_ALIGN_MIN_PX, round(crop_px * LOCAL_CROP_ALIGN_CONTEXT_FACTOR)))
    context_px = min(context_px, max(1, min(img_w, img_h)))
    x1, y1, x2, y2 = crop_bounds(candidate.cx, candidate.cy, img_w, img_h, context_px)
    ref_patch = ref_img[y1:y2, x1:x2]
    patch = img[y1:y2, x1:x2]
    if ref_patch.shape[:2] != patch.shape[:2] or min(ref_patch.shape[:2]) < 64:
        return candidate.cx, candidate.cy, None

    size = (ref_patch.shape[1], ref_patch.shape[0])
    try:
        ref_grad = alignment_image(ref_patch, size)
        patch_grad = alignment_image(patch, size)
        window = cv2.createHanningWindow(size, cv2.CV_32F)
        (dx, dy), response = cv2.phaseCorrelate(patch_grad, ref_grad, window)
    except cv2.error:
        return candidate.cx, candidate.cy, None

    shift = math.hypot(dx, dy)
    max_shift = max(LOCAL_CROP_ALIGN_MIN_ACCEPTED_SHIFT_PX, crop_px * max_shift_factor)
    info = {
        "method": "local_phase",
        "dx": round(float(dx), 2),
        "dy": round(float(dy), 2),
        "response": round(float(response), 4),
        "context_px": context_px,
        "min_response": round(float(min_response), 4),
        "max_shift": round(float(max_shift), 2),
    }
    if response < min_response or shift > max_shift:
        return candidate.cx, candidate.cy, {**info, "accepted": False}

    return candidate.cx - dx, candidate.cy - dy, {**info, "accepted": True}


def weak_detection_crop(obs: Observation | None) -> bool:
    if obs is None or obs.crop_cx is None or obs.crop_cy is None:
        return False
    if obs.dist_m is not None and obs.dist_m > DETECTION_CROP_MAX_DIST_M:
        return True
    return obs.match_score is not None and obs.match_score < DETECTION_CROP_MIN_MATCH_SCORE


def save_candidate_crops(
    items: list[ImageItem],
    ref_item: ImageItem,
    candidates: list[Candidate],
    crops_dir: Path,
    manifest_path: Path,
    img_w: int,
    img_h: int,
    crop_px: int,
) -> None:
    ref_img = aligned_image(ref_item)
    for item in items:
        item.crops = []
    manifest: dict[str, Any] = {
        "crop_px": crop_px,
        "items": [item.label for item in items],
        "candidates": [],
    }
    for i, candidate in enumerate(candidates):
        manifest_candidate = {
            "rank": i + 1,
            "lat": candidate.lat,
            "lon": candidate.lon,
            "base_center": {"x": round(float(candidate.cx), 2), "y": round(float(candidate.cy), 2)},
            "crops": [],
        }
        for item_idx, item in enumerate(items):
            img = aligned_image(item)
            obs = candidate.observations[item_idx] if item_idx < len(candidate.observations) else None
            crop_source = (
                "matched_detection" if obs and obs.crop_cx is not None and obs.crop_cy is not None else "reference"
            )
            local_align = None
            if crop_source == "matched_detection":
                crop_cx = obs.crop_cx
                crop_cy = obs.crop_cy
                if weak_detection_crop(obs):
                    local_cx, local_cy, local_align = local_aligned_crop_center(
                        ref_img,
                        img,
                        candidate,
                        img_w,
                        img_h,
                        crop_px,
                        min_response=LOCAL_CROP_ALIGN_WEAK_DET_MIN_RESPONSE,
                    )
                    if local_align and local_align.get("accepted"):
                        local_align["replaced_detection"] = {
                            "center_x": round(float(crop_cx), 2),
                            "center_y": round(float(crop_cy), 2),
                            "dist_m": obs.dist_m,
                            "match_score": obs.match_score,
                        }
                        crop_cx = local_cx
                        crop_cy = local_cy
                        crop_source = "weak_detection_local_alignment"
            else:
                crop_cx, crop_cy, local_align = local_aligned_crop_center(
                    ref_img,
                    img,
                    candidate,
                    img_w,
                    img_h,
                    crop_px,
                    min_response=LOCAL_CROP_ALIGN_REFERENCE_MIN_RESPONSE,
                    max_shift_factor=LOCAL_CROP_ALIGN_REFERENCE_MAX_SHIFT_FACTOR,
                )
                if local_align and local_align.get("accepted"):
                    crop_source = "local_alignment"
            x1, y1, x2, y2 = crop_bounds(crop_cx, crop_cy, img_w, img_h, crop_px)
            chunk = img[y1:y2, x1:x2]
            if chunk.size == 0:
                item.crops.append({"file": None})
            else:
                name = f"cand_{i:03d}_{item.label}.jpg"
                path = crops_dir / name
                cv2.imwrite(str(path), chunk, [cv2.IMWRITE_JPEG_QUALITY, REVIEW_JPEG_QUALITY])
                item.crops.append(
                    {
                        "file": f"crops/{name}",
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "center_x": round(float(crop_cx), 2),
                        "center_y": round(float(crop_cy), 2),
                        "center_source": crop_source,
                        "local_alignment": local_align,
                    }
                )
            crop_entry = item.crops[-1] if item.crops else {"file": None}
            manifest_candidate["crops"].append(
                {
                    "label": item.label,
                    "status": obs.status if obs else None,
                    "conf": round(obs.conf, 3) if obs and obs.conf is not None else None,
                    "dist_m": round(obs.dist_m, 2) if obs and obs.dist_m is not None else None,
                    "match_score": round(obs.match_score, 3) if obs and obs.match_score is not None else None,
                    "detection_center": (
                        {"x": round(obs.crop_cx, 2), "y": round(obs.crop_cy, 2)}
                        if obs and obs.crop_cx is not None and obs.crop_cy is not None
                        else None
                    ),
                    "final_center": (
                        {"x": crop_entry.get("center_x"), "y": crop_entry.get("center_y")}
                        if crop_entry.get("file")
                        else None
                    ),
                    "center_source": crop_entry.get("center_source"),
                    "local_alignment": crop_entry.get("local_alignment"),
                    "file": crop_entry.get("file"),
                }
            )
        manifest["candidates"].append(manifest_candidate)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

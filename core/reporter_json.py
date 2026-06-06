from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.models import Candidate, Observation


def observation_to_json(obs: Observation) -> dict[str, Any]:
    return {
        "label": obs.label,
        "status": obs.status,
        "reason": obs.reason,
        "conf": round(obs.conf, 3) if obs.conf is not None else None,
        "dist_m": round(obs.dist_m, 2) if obs.dist_m is not None else None,
        "angle_diff": round(obs.angle_diff, 1) if obs.angle_diff is not None else None,
        "color_similarity": round(obs.color_similarity, 3) if obs.color_similarity is not None else None,
        "shape_similarity": round(obs.shape_similarity, 3) if obs.shape_similarity is not None else None,
        "match_score": round(obs.match_score, 3) if obs.match_score is not None else None,
        "crop_cx": round(obs.crop_cx, 2) if obs.crop_cx is not None else None,
        "crop_cy": round(obs.crop_cy, 2) if obs.crop_cy is not None else None,
    }


def candidates_to_json(candidates: list[Candidate]) -> list[dict[str, Any]]:
    out_json: list[dict[str, Any]] = []
    for i, candidate in enumerate(candidates):
        out_json.append(
            {
                "rank": i + 1,
                "score": round(candidate.score, 4),
                "current_conf": round(candidate.current_conf, 4),
                "coverage": round(candidate.coverage, 3),
                "color_consistency": round(candidate.color_consistency, 3),
                "mean_conf": round(candidate.mean_conf, 3),
                "mean_match": round(candidate.mean_match, 3),
                "span_score": round(candidate.span_score, 3),
                "evidence_factor": round(candidate.evidence_factor, 3),
                "n_detections": candidate.n_detections,
                "valid_items": candidate.valid_items,
                "ignored_count": candidate.ignored_count,
                "clear_missing_count": candidate.clear_missing_count,
                "labels_present": candidate.labels_present,
                "observations": [observation_to_json(obs) for obs in candidate.observations],
                "lat": candidate.lat,
                "lon": candidate.lon,
            }
        )
    return out_json


def save_candidates_json(candidates: list[Candidate], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(candidates_to_json(candidates), f, indent=2, ensure_ascii=False)

import inspect
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import core.reporter as reporter
import core.reporter_html as reporter_html
from core.models import Candidate, ImageItem, Observation
from core.reporter import write_analysis_outputs
from core.reporter_json import candidates_to_json


class ReporterModuleBoundaryTests(unittest.TestCase):
    def test_reporter_keeps_split_helpers_out_of_orchestration_module(self):
        for helper_name in (
            "candidates_to_json",
            "observation_to_json",
            "render_report",
            "save_candidate_crops",
            "save_candidates_json",
            "save_overlay",
        ):
            self.assertNotIn(helper_name, reporter.__dict__)

    def test_candidate_json_lives_in_json_module(self):
        candidate = Candidate(
            cx=10.0,
            cy=20.0,
            lat=51.0,
            lon=17.0,
            score=0.75,
            current_conf=0.8,
            coverage=1.0,
            color_consistency=0.9,
            mean_conf=0.8,
            mean_match=0.7,
            span_score=0.6,
            evidence_factor=1.0,
            labels_present=["2025"],
            n_detections=1,
            valid_items=1,
            ignored_count=0,
            clear_missing_count=0,
            observations=[Observation(label="2025", status="present", conf=0.8)],
            poly=np.array([[0, 0], [1, 0], [1, 1]], dtype=np.float32),
        )

        self.assertEqual(candidates_to_json([candidate])[0]["rank"], 1)

    def test_analysis_report_html_renderer_stays_composed_from_helpers(self):
        render_source, _ = inspect.getsourcelines(reporter_html.render_report)

        self.assertLessEqual(len(render_source), 45)
        self.assertIn("REPORT_CSS", reporter_html.__dict__)
        self.assertIn("REPORT_SCRIPT_TEMPLATE", reporter_html.__dict__)


class ReportAssetCacheContractTests(unittest.TestCase):
    def test_report_versions_overwritten_image_assets(self):
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            crops_dir = output_dir / "crops"
            overlay_dir = output_dir / "overlays"
            crops_dir.mkdir()
            overlay_dir.mkdir()

            img = np.full((80, 80, 3), 120, dtype=np.uint8)
            items = [
                ImageItem(source="test", label="2024", path=Path("ortofoto_2024.png"), img=img.copy()),
                ImageItem(source="test", label="2025", path=Path("ortofoto_2025.png"), img=img.copy()),
            ]
            candidate = Candidate(
                cx=40.0,
                cy=40.0,
                lat=51.0,
                lon=17.0,
                score=0.9,
                current_conf=0.8,
                coverage=1.0,
                color_consistency=0.9,
                mean_conf=0.8,
                mean_match=0.8,
                span_score=1.0,
                evidence_factor=1.0,
                labels_present=["2024", "2025"],
                n_detections=2,
                valid_items=2,
                ignored_count=0,
                clear_missing_count=0,
                observations=[
                    Observation(label="2024", status="present", conf=0.8, crop_cx=40.0, crop_cy=40.0),
                    Observation(label="2025", status="present", conf=0.9, crop_cx=40.0, crop_cy=40.0),
                ],
                poly=np.array([[35, 35], [45, 35], [45, 45], [35, 45]], dtype=np.float32),
            )

            write_analysis_outputs(
                items,
                items[1],
                [candidate],
                output_dir,
                crops_dir,
                overlay_dir,
                img_w=80,
                img_h=80,
                eps_px=5.0,
                crop_px=20,
            )

            html = (output_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn('src="overlays/scored_overlay.jpg?v=', html)
            self.assertIn('src="crops/cand_000_2024.jpg?v=', html)
            self.assertIn('src="crops/cand_000_2025.jpg?v=', html)
            self.assertNotIn('src="overlays/scored_overlay.jpg"', html)
            self.assertNotIn('src="crops/cand_000_2024.jpg"', html)

            manifest = json.loads((output_dir / "crop_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["candidates"][0]["crops"][0]["file"], "crops/cand_000_2024.jpg")


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("design_loop.py")
spec = importlib.util.spec_from_file_location("design_loop", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class DesignLoopTests(unittest.TestCase):
    def test_black_white_contrast_matches_wcag_reference(self):
        self.assertAlmostEqual(module.contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=2)

    def test_design_spec_round_trips_as_json(self):
        original = module.DesignSpec(width=800, accent="#123456", title="Probe")
        restored = module.DesignSpec.from_mapping(json.loads(json.dumps(original.to_json())))
        self.assertEqual(restored, original)

    def test_heuristic_reviewer_improves_the_initial_spec(self):
        original = module.DesignSpec()
        analysis = module.DesignAnalysis(
            iteration=0,
            screenshot="probe.png",
            width=original.width,
            height=original.height,
            background_rgb=(215, 215, 215),
            mean_luma=0.7,
            luma_stddev=0.1,
            non_background_ratio=0.5,
            text_contrast=1.5,
            muted_contrast=1.2,
            accent_contrast=1.1,
            white_on_accent_contrast=2.0,
            score=module.spec_quality(original),
            issues=("low contrast",),
        )
        improved = module.HeuristicReviewer().improve(original, analysis)
        self.assertGreater(module.spec_quality(improved), module.spec_quality(original))
        self.assertEqual(improved.width, 720)
        self.assertEqual(improved.height, 420)
        self.assertEqual(improved.margin, 32)

    def test_unknown_design_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            module.DesignSpec.from_mapping({"not_a_design_field": True})


if __name__ == "__main__":
    unittest.main()

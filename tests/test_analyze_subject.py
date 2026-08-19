import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "skills" / "animated-video-workflow" / "scripts" / "analyze_subject.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_subject", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnalyzeSubjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_face_expands_to_talking_head_region(self):
        body = self.module.estimate_body_from_face((0.42, 0.12, 0.12, 0.12))
        self.assertLess(body[0], 0.42)
        self.assertGreater(body[2], 0.12)
        self.assertGreater(body[3], 0.12)

    def test_primary_subject_prefers_previous_track(self):
        previous = (0.08, 0.2, 0.25, 0.6)
        choices = [(0.1, 0.2, 0.25, 0.6), (0.65, 0.1, 0.3, 0.75)]
        self.assertEqual(self.module.choose_primary(choices, previous), choices[0])

    def test_build_report_creates_shot_safe_regions(self):
        samples = [
            self.module.Sample(0.0, [(0.05, 0.45, 0.2, 0.45)], 0.0),
            self.module.Sample(1.0, [(0.08, 0.43, 0.2, 0.47)], 0.1),
            self.module.Sample(2.0, [(0.62, 0.1, 0.3, 0.8)], 0.8),
            self.module.Sample(3.0, [(0.6, 0.1, 0.32, 0.8)], 0.1),
        ]
        report = self.module.build_report(
            pathlib.Path("talk.mp4"), 1920, 1080, 4.0, 1.0, 0.52, samples
        )
        self.assertEqual(len(report["shots"]), 2)
        self.assertIsNotNone(report["shots"][0]["subject_safe_region"])
        self.assertFalse(report["shots"][0]["review_required"])

    def test_low_confidence_requires_review(self):
        samples = [
            self.module.Sample(0.0, [], 0.0),
            self.module.Sample(1.0, [], 0.1),
        ]
        report = self.module.build_report(
            pathlib.Path("talk.mp4"), 1080, 1920, 2.0, 1.0, 0.52, samples
        )
        self.assertTrue(report["review_required"])
        self.assertEqual(report["shots"][0]["layout_type"], "unknown")


if __name__ == "__main__":
    unittest.main()

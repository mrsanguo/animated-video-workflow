import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "skills" / "animated-video-workflow" / "scripts" / "validate_plan.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_plan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidatePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_accepts_video_only_manifest(self):
        manifest = {
            "version": 1,
            "mode": "semi-auto",
            "rough_cut_requested": False,
            "inputs": {"video": "input/talk.mp4"},
            "outputs": {"aspects": ["16:9", "9:16"]},
        }
        self.module.validate_manifest(manifest)

    def test_accepts_ordered_storyboard(self):
        storyboard = {
            "version": 1,
            "scenes": [
                {"id": "s1", "start": 0, "end": 2.5, "visual_type": "live"},
                {"id": "s2", "start": 2.5, "end": 5, "visual_type": "animation"},
            ],
        }
        self.module.validate_storyboard(storyboard)

    def test_rejects_invalid_scene_bounds(self):
        storyboard = {
            "version": 1,
            "scenes": [{"id": "s1", "start": 2, "end": 2, "visual_type": "live"}],
        }
        with self.assertRaisesRegex(ValueError, "start must be before end"):
            self.module.validate_storyboard(storyboard)

    def test_rejects_overlapping_scenes(self):
        storyboard = {
            "version": 1,
            "scenes": [
                {"id": "s1", "start": 0, "end": 3, "visual_type": "live"},
                {"id": "s2", "start": 2.5, "end": 4, "visual_type": "image"},
            ],
        }
        with self.assertRaisesRegex(ValueError, "overlaps"):
            self.module.validate_storyboard(storyboard)

    def test_rejects_unknown_visual_type_and_engine(self):
        with self.assertRaisesRegex(ValueError, "visual_type"):
            self.module.validate_storyboard(
                {"version": 1, "scenes": [{"id": "s1", "start": 0, "end": 1, "visual_type": "magic"}]}
            )
        with self.assertRaisesRegex(ValueError, "engine"):
            self.module.validate_render_plan(
                {"version": 1, "scenes": [{"scene_id": "s1", "engine": "unknown"}]},
                {"s1"},
            )

    def test_rough_cut_artifacts_follow_request(self):
        manifest = {
            "version": 1,
            "mode": "semi-auto",
            "rough_cut_requested": False,
            "inputs": {"video": "input/talk.mp4"},
            "outputs": {"aspects": ["16:9", "9:16"]},
            "rough_cut": {"video": "work/rough-cut.mp4"},
        }
        with self.assertRaisesRegex(ValueError, "rough_cut"):
            self.module.validate_manifest(manifest)

    def test_accepts_subject_layout(self):
        layout = {
            "version": 1,
            "canvas": {"width": 1920, "height": 1080},
            "coordinate_space": "normalized",
            "shots": [
                {
                    "id": "shot-001",
                    "start": 0,
                    "end": 5,
                    "confidence": 0.9,
                    "layout_type": "picture-in-picture",
                    "primary_motion_envelope": {"x": 0.02, "y": 0.6, "width": 0.2, "height": 0.35},
                    "subject_safe_region": {"x": 0, "y": 0.54, "width": 0.26, "height": 0.46},
                    "animation_regions": [
                        {"side": "right", "x": 0.3, "y": 0.07, "width": 0.65, "height": 0.76}
                    ],
                    "review_required": False,
                }
            ],
        }
        self.module.validate_subject_layout(layout)

    def test_rejects_subject_region_outside_canvas(self):
        layout = {
            "version": 1,
            "canvas": {"width": 1080, "height": 1920},
            "coordinate_space": "normalized",
            "shots": [
                {
                    "id": "shot-001",
                    "start": 0,
                    "end": 5,
                    "confidence": 0.8,
                    "layout_type": "portrait-presenter",
                    "subject_safe_region": {"x": 0.8, "y": 0.1, "width": 0.4, "height": 0.8},
                    "primary_motion_envelope": None,
                    "animation_regions": [],
                    "review_required": True,
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "fit the canvas"):
            self.module.validate_subject_layout(layout)


if __name__ == "__main__":
    unittest.main()

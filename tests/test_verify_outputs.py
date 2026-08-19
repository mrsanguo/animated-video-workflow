import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "skills" / "animated-video-workflow" / "scripts" / "verify_outputs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_outputs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerifyOutputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def create_base_project(self, root, *, searched=False, copyright_review=True):
        root = pathlib.Path(root)
        (root / "work").mkdir(parents=True)
        (root / "output").mkdir()
        for name in ("storyboard.json", "render-plan.json"):
            (root / "work" / name).write_text("{}\n", encoding="utf-8")
        assets = [{"id": "a1", "source_url": "https://example.com/a"}] if searched else []
        (root / "work" / "asset-register.json").write_text(
            json.dumps({"version": 1, "assets": assets}), encoding="utf-8"
        )
        if copyright_review:
            (root / "work" / "copyright-review.md").write_text("# Review\n", encoding="utf-8")

    def add_outputs(self, root, *, versioned=True):
        output = pathlib.Path(root) / "output"
        names = (
            ("final-16x9-v1.mp4", "final-9x16-v1.mp4")
            if versioned
            else ("final-16x9.mp4", "final-9x16.mp4")
        )
        for name in names:
            (output / name).write_bytes(b"video")

    def unavailable_probe(self, _):
        return {"status": "unavailable", "reason": "test fixture"}

    def test_detects_missing_deliverables(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_base_project(tmp)
            report = self.module.verify_project(pathlib.Path(tmp), probe=self.unavailable_probe)
            self.assertEqual(report["status"], "fail")
            self.assertTrue(any("final-16x9" in item["name"] for item in report["checks"] if item["status"] == "fail"))

    def test_accepts_both_aspect_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_base_project(tmp)
            self.add_outputs(tmp)
            report = self.module.verify_project(pathlib.Path(tmp), probe=self.unavailable_probe)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(len(report["outputs"]), 2)

    def test_requires_copyright_review_for_searched_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_base_project(tmp, searched=True, copyright_review=False)
            self.add_outputs(tmp)
            report = self.module.verify_project(pathlib.Path(tmp), probe=self.unavailable_probe)
            self.assertEqual(report["status"], "fail")
            self.assertTrue(any(item["name"] == "copyright-review-present" for item in report["checks"]))

    def test_rejects_unversioned_output_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_base_project(tmp)
            self.add_outputs(tmp, versioned=False)
            report = self.module.verify_project(pathlib.Path(tmp), probe=self.unavailable_probe)
            self.assertEqual(report["status"], "fail")

    def test_writes_qc_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.create_base_project(tmp)
            self.add_outputs(tmp)
            report_path = pathlib.Path(tmp) / "work" / "qc-report.json"
            result = self.module.run(pathlib.Path(tmp), report_path, probe=self.unavailable_probe)
            self.assertEqual(result, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")


if __name__ == "__main__":
    unittest.main()

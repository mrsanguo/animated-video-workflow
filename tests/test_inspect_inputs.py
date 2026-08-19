import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "skills" / "animated-video-workflow" / "scripts" / "inspect_inputs.py"


def load_module():
    spec = importlib.util.spec_from_file_location("inspect_inputs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InspectInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def make_files(self, root, names):
        for name in names:
            path = pathlib.Path(root) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")

    def test_video_plus_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["talk.mp4", "talk.srt"])
            manifest = self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})
            self.assertTrue(manifest["inputs"]["video"].endswith("talk.mp4"))
            self.assertTrue(manifest["inputs"]["subtitle"].endswith("talk.srt"))
            self.assertFalse(manifest["transcription_needed"])

    def test_audio_plus_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["voice.wav", "voice.txt"])
            manifest = self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})
            self.assertTrue(manifest["inputs"]["audio"].endswith("voice.wav"))
            self.assertTrue(manifest["inputs"]["script"].endswith("voice.txt"))
            self.assertTrue(manifest["transcription_needed"])

    def test_video_only_needs_transcription(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["raw.mov"])
            manifest = self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})
            self.assertTrue(manifest["transcription_needed"])

    def test_rejects_directory_without_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["notes.md", "unknown.bin"])
            with self.assertRaisesRegex(ValueError, "video or audio"):
                self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})

    def test_records_unsupported_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["talk.mp4", "archive.xyz"])
            manifest = self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})
            self.assertTrue(manifest["unsupported_files"][0].endswith("archive.xyz"))

    def test_rough_cut_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_files(tmp, ["talk.mp4"])
            normal = self.module.inspect_directory(pathlib.Path(tmp), probe=lambda _: {"status": "ok"})
            requested = self.module.inspect_directory(
                pathlib.Path(tmp), rough_cut=True, probe=lambda _: {"status": "ok"}
            )
            self.assertFalse(normal["rough_cut_requested"])
            self.assertTrue(requested["rough_cut_requested"])
            self.assertTrue((pathlib.Path(tmp) / "talk.mp4").exists())


if __name__ == "__main__":
    unittest.main()

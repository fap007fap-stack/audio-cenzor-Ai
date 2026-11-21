"""Repository integrity tests: checks required files and the standalone module imports."""
import unittest
from pathlib import Path


class DeploymentTests(unittest.TestCase):
    def test_root_files_present(self):
        base = Path(__file__).resolve().parent
        required = ("app.py", "audio_engine.py", "detectors.py", "quality_checks.py",
                    "speech.py", "style.css", "requirements.txt", "packages.txt")
        self.assertFalse([f for f in required if not (base / f).is_file()])

    def test_engine_imports(self):
        import audio_engine
        import detectors
        import quality_checks
        import speech
        self.assertTrue(hasattr(audio_engine, "export_audio"))
        self.assertTrue(hasattr(detectors, "detect_all"))
        self.assertTrue(hasattr(quality_checks, "redaction_report"))
        self.assertTrue(hasattr(speech, "transcribe"))


if __name__ == "__main__":
    unittest.main()

"""Offline smoke tests for AI pipeline diagnostics, no model downloads."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from detectors import Token, detect_all
from speech import transcribe


class FakeWhisper:
    def __init__(self, segments):
        self.segments = segments
        self.args = None

    def transcribe(self, path, **kwargs):
        self.args = (path, kwargs)
        return iter(self.segments), SimpleNamespace(language="pl")


class AiSmokeTests(unittest.TestCase):
    def test_word_timestamps_feed_detector(self):
        words = ["Nazywam", "się", "Jan", "Kowalski", "telefon", "501", "234", "567", "kurwa"]
        segments = [SimpleNamespace(words=[SimpleNamespace(word=w, start=i * .5, end=(i+1)*.5)
                                            for i, w in enumerate(words)], text=" ".join(words),
                                    start=0, end=4.5)]
        model = FakeWhisper(segments)
        with patch("speech.wav_as_float32", return_value=np.zeros(1600, dtype=np.float32)):
            tokens = transcribe(Path("sample.wav"), model)
        self.assertEqual(len(tokens), len(words))
        self.assertIsInstance(model.args[0], np.ndarray)
        self.assertEqual(model.args[1]["language"], "pl")
        self.assertTrue(model.args[1]["word_timestamps"])
        _, findings = detect_all(tokens, {"Imiona i nazwiska", "Numery telefonów", "Wulgaryzmy"})
        actual = {found.category for found in findings}
        self.assertTrue({"Imiona i nazwiska", "Numery telefonów", "Wulgaryzmy"}.issubset(actual))

    def test_transcript_without_word_offsets_retained_for_review(self):
        model = FakeWhisper([SimpleNamespace(words=None, text=" Nazwa testowa ", start=.3, end=1.8)])
        with patch("speech.wav_as_float32", return_value=np.zeros(1600, dtype=np.float32)):
            tokens = transcribe(Path("sample.wav"), model)
        self.assertEqual(tokens, [Token("Nazwa testowa", .3, 1.8)])

    def test_app_deprecated_options_replaced(self):
        source = (Path(__file__).resolve().parent / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("use_container_width=", source)
        self.assertIn('APP_VERSION = "1.7.1"', source)
        self.assertIn('with st.status(', source)

    def test_demo_detector_independent_of_ner_model(self):
        words = "Nazywam się Jan Kowalski telefon 501 234 567 kurwa".split()
        tokens = [Token(w, i * .4, (i + 1) * .4) for i, w in enumerate(words)]
        _, findings = detect_all(tokens, {"Wulgaryzmy", "Numery telefonów", "Imiona i nazwiska"})
        self.assertGreaterEqual(len(findings), 3)


if __name__ == "__main__":
    unittest.main()
